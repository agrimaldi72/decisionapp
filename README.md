1) Reemplazar en el archivo cp4na.credential.properties por los valores correspondientes:
   
    username = **\<username to access CP4NA\>**
    
    api_key = **\<API KEY generated for this username\>**
    
    auth_url = https://**<CP4NA fqdn\>**/icp4d-api/v1/authorize


2) Kustomize deployment base está armado para que la app decisionapp se instale en NS cp4na, si quiere usar otro namespace cree un overlay
