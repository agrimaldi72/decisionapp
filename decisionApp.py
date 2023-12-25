from flask import Flask
from flask import render_template
from flask import request, redirect, url_for
import requests
import json
import jwt
import time, datetime
from kubernetes import client, config


app = Flask(__name__)
bearerToken = ""
expToken = int(time.time())  
sethighqps=False
setnormalqps=False
sethighcpu={}



#Para app corriendo dentro del cluster que corre el servicio
config.load_incluster_config()

#Para app corriendo fuera del cluster que corre el servicio
#config.load_kube_config(config_file="C:\\Users\\u604203\\.kube\\config")

@app.route('/',methods = ['GET','POST'])
def health():
  return "it's Ok!!!!"

#Para alarmas recibidas desde Alertmanager
#@app.route('/alertmanager',methods = ['POST'])

#Para alarmas recibidas desde Prometheus
@app.route('/api/v2/alerts',methods = ['POST'])
def alertManager():
  global assemblyId
  global brokenComponentId
  global clusterId
  global sethighqps
  global setnormalqps
  global sethighcpu


  arrivetime = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
  content_type = request.headers.get('Content-Type')
  if (content_type == 'application/json'):
      json = request.json

      alertname = json[0]['labels']['alertname']
      startsat = json[0]['startsAt']
      endsat = json[0]['endsAt']     

      if (alertname == 'High CPU'):   
        podname = json[0]['labels']['pod']
        namespace = json[0]['labels']['namespace']

        if podname not in sethighcpu:
           sethighcpu[podname]=False

        if ((endsat > arrivetime) and not(sethighcpu[podname])):
            sethighcpu[podname]=True
      #consulta a la API de K8S para obtener el annotation del PoD para determinar el nombre en CP4NA
            Pod = client.CoreV1Api().read_namespaced_pod(name=podname,namespace=namespace,pretty='true')
            Metadata = Pod.metadata
            Annotation = Metadata.annotations
            ResourceName = Annotation['cp4na/resourceName']
            ResourceNameSplitted = ResourceName.split('__')
            AssemblyName = ResourceNameSplitted[0]
            ClusterName = ResourceNameSplitted[0] + "__" + ResourceNameSplitted[1]
            return (healing(AssemblyName, ResourceName))
      
        if ((endsat <= arrivetime) and (sethighcpu[podname])):
            sethighcpu[podname]=False
            return 'Normal CPU' 
        return 'Nothing to do' 
      else:
      #valores hardcoded, requiere instanciar servicio pdns con nombre dns-service  
        AssemblyName = 'dns-service'
        ResourceName = 'dns-service__pdns-resolver'
        ClusterName = 'dns-service__pdns-resolver'         


      if ((alertname == 'High QPS') and (endsat > arrivetime) and not(sethighqps)):
          sethighqps=True
          setnormalqps=False
          return (scaleOut(AssemblyName, ClusterName))
      if ((alertname == 'High QPS') and (endsat <= arrivetime) and (sethighqps)):
          sethighqps=False
          return 'In Band Down' 
      
      if ((alertname == 'Normal QPS') and (endsat > arrivetime) and not(setnormalqps)):
          sethighqps=False
          setnormalqps=True
          return (scaleIn(AssemblyName, ClusterName))
      if ((alertname == 'Normal QPS') and (endsat <= arrivetime) and (setnormalqps)):
          setnormalqps=False
          return 'In Band Up' 
      return 'Nothing to do'      
  else:
      return 'Content-Type not supported!'
  
def getCredential(archivo):
  credential = {}
  with open(archivo) as myfile:
    for line in myfile:
      name, var = line.partition("=")[::2]
      credential[name.strip()] = var.strip()
    return credential

def healing(assemblyId, brokenComponentId):
  bearerToken = getAuthToken()
  url = "https://cp4na-o-ishtar-cp4na.apps.okd.cablevision-labs.com.ar/api/v1/intent/healAssembly"

  headers = {
    'Authorization': f'Bearer {bearerToken}',
    'Content-Type': 'application/json'
    }

  payload = json.dumps({
    "assemblyName": assemblyId,
    "brokenComponentName": brokenComponentId
  })

  response = requests.request("POST", url, headers=headers, data=payload ,verify=False)

  if (response.status_code == 200):
    return json.loads(response.text)
  elif (response.status_code == 201):
    return response.text
  else:
    return ("Assembly no encontrado")


def getAuthToken():
  url = "https://cpd-cp4na.apps.okd.cablevision-labs.com.ar/icp4d-api/v1/authorize"
  global bearerToken
  global expToken

  if (bearerToken == "") or (expToken < int(time.time())):
    credential=getCredential("cp4na.credential.properties")
    payload = json.dumps({
      "username": credential["username"],
      "api_key": credential["api_key"]
    })
    print(payload)
    headers = {
      'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload,verify=False)

    bearerToken = json.loads(response.text)["token"]
  
    decoded_data = jwt.decode(jwt=bearerToken,
                              key='secret',
                              algorithms=["RS256"],
                              options={"verify_signature": False})
    expToken = decoded_data["exp"]
    print ("Se renueva bearer Token \n")

  return bearerToken

def scaleIn(assemblyId, clusterId):
  bearerToken = getAuthToken()
  url = "https://cp4na-o-ishtar-cp4na.apps.okd.cablevision-labs.com.ar/api/v1/intent/scaleInAssembly"

  headers = {
    'Authorization': f'Bearer {bearerToken}',
    'Content-Type': 'application/json'
    }

  payload = json.dumps({
    "assemblyName": assemblyId,
    "clusterName": clusterId
  })

  response = requests.request("POST", url, headers=headers, data=payload ,verify=False)

  if (response.status_code == 200):
    return json.loads(response.text)
  elif (response.status_code == 201):
    return response.text
  elif (response.status_code == 500):
    return response.text
  else:
    return ("Falla de escalado")



def scaleOut(assemblyId, clusterId):
  bearerToken = getAuthToken()
  url = "https://cp4na-o-ishtar-cp4na.apps.okd.cablevision-labs.com.ar/api/v1/intent/scaleOutAssembly"

  headers = {
    'Authorization': f'Bearer {bearerToken}',
    'Content-Type': 'application/json'
    }

  payload = json.dumps({
    "assemblyName": assemblyId,
    "clusterName": clusterId
  })

  response = requests.request("POST", url, headers=headers, data=payload ,verify=False)

  if (response.status_code == 200):
    return json.loads(response.text)
  elif (response.status_code == 201):
    return response.text
  elif (response.status_code == 500):
    return response.text
  else:
    return ("Falla de escalado")



if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)