targetScope = 'subscription'

// The main bicep module to provision Azure resources for the AI Transcript App backend.
// Adapted from the Azure "Deploy a Python web app to App Service" quickstart
// (https://github.com/Azure-Samples/msdocs-python-flask-webapp-quickstart) to deploy
// the FastAPI backend (backend/) to Azure App Service via the Azure Developer CLI (azd).
// For how this file works with azd, see
// https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/make-azd-compatible?pivots=azd-create

@minLength(1)
@maxLength(64)
@description('Name of the the environment which is used to generate a short unique hash used in all resources.')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string

// Optional parameters to override the default azd resource naming conventions.
param resourceGroupName string = ''
param appServiceName string = ''
param appServicePlanName string = ''

// Application settings for the transcript app's LLM cleanup step (OpenAI-compatible).
// Set these via `azd env set <NAME> <value>` before `azd up`.
@description('Base URL of an OpenAI-compatible LLM endpoint used for transcript cleanup.')
param llmBaseUrl string = ''
@secure()
@description('API key for the LLM endpoint (ignored by some local providers).')
param llmApiKey string = ''
@description('Model name used for transcript cleanup.')
param llmModel string = ''
@description('Whisper speech-to-text model name.')
param whisperModel string = 'base.en'

var abbrs = loadJsonContent('./abbreviations.json')

// tags that should be applied to all resources.
var tags = {
  'azd-env-name': environmentName
}

// Generate a unique token to be used in naming resources.
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))

// Organize resources in a resource group
resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: !empty(resourceGroupName) ? resourceGroupName : '${abbrs.resourcesResourceGroups}${environmentName}'
  location: location
  tags: tags
}

// Only include LLM settings that have been provided so the app can also run
// transcription-only on App Service if no LLM endpoint is configured.
var llmAppSettings = union(
  { WHISPER_MODEL: whisperModel },
  !empty(llmBaseUrl) ? { LLM_BASE_URL: llmBaseUrl } : {},
  !empty(llmApiKey) ? { LLM_API_KEY: llmApiKey } : {},
  !empty(llmModel) ? { LLM_MODEL: llmModel } : {}
)

// The FastAPI backend App
module web './core/host/appservice.bicep' = {
  name: 'web'
  scope: rg
  params: {
    name: !empty(appServiceName) ? appServiceName : '${abbrs.webSitesAppService}web-${resourceToken}'
    location: location
    appServicePlanId: appServicePlan.outputs.id
    runtimeName: 'python'
    runtimeVersion: '3.12'
    // FastAPI is served with uvicorn; App Service exposes the app on port 8000.
    appCommandLine: 'python -m uvicorn app:app --host 0.0.0.0 --port 8000'
    scmDoBuildDuringDeployment: true
    appSettings: llmAppSettings
    tags: union(tags, { 'azd-service-name': 'web' })
  }
}

// Create an App Service Plan to group applications under the same payment plan and SKU
module appServicePlan './core/host/appserviceplan.bicep' = {
  name: 'appserviceplan'
  scope: rg
  params: {
    name: !empty(appServicePlanName) ? appServicePlanName : '${abbrs.webServerFarms}${resourceToken}'
    location: location
    tags: tags
    sku: {
      name: 'B1'
    }
  }
}

// Outputs are automatically saved in the local azd environment .env file.
output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output WEB_URI string = web.outputs.uri
