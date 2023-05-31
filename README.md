# VIRA Dialog Manager
This repository contains code and data to build the dialog manager of the VIRA chatbot, addressing concerns surrounding COVID-19 vaccines.

## Setup
### Create a conda environment
```shell
conda create -n vira_env python=3.9
conda activate vira_env
pip install -r requirements
```
### Setting up access to the database
1. Create a directory to store files needed to access the database:
```shell
mkdir resources/db
```
2. Place in it a certificate.crt file and a db_credentials.json file. The db_credentials.json file should contain the following keys: username (string), password (string), and endpoint (list of strings).

### Uploading VIRA content to the database
The script to upload the content in resources to the db is in `db_utils.py`.

To run it, first define the following environment variables: 

'BOT_WA_APIKEY': The API key of the translation service

'BOT_WA_URL': The url of the translation service 

'BOT_DASHBOARD_CODE': The code required to access the evaluation dashboard (currently not active, can be left empty)

'BOT_KPA_HOST': The url of the KPA service in the evaluation dashboard (currently not active, can be left empty)

'BOT_KPA_APIKEY': The API key of the KPA service in the evaluation dashboard (currently not active, can be left empty)

'BOT_INTENT_CLASSIFIER_URL': The url of intent / key-point matching service of VIRA

'BOT_DIALOG_ACT_CLASSIFIER_URL': The url of the dialog-act service of VIRA

Then run
```shell
python db_utils.py -conf-canned-db
```

## Testing VIRA
To launch VIRA in your local environment, set 'VIRA_API_KEY' to contain an API key, and run
```shell
python main.py
```
To test VIRA with a simple question, set the environment variable 'VIRA_API_KEY' that should contain the API key set launching VIRA, and run
```shell
python sanity.py
```

## License

If you would like to see the detailed LICENSE click [here](LICENSE).
