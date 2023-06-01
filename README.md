# VIRA Dialog Manager
This repository contains code and data to build the dialog manager of the VIRA chatbot, addressing concerns surrounding COVID-19 vaccines.

## Setup
### Create a Conda Environment
```shell
conda create -n vira_env python=3.9
conda activate vira_env
pip install -r requirements.txt
```
### Setting up Access to the MongoDB Database
1. Create a directory to store files needed to access the database:
```shell
mkdir resources/db
```
2. Place in it a `db_credentials.json` file and a `certificate.crt` file. The `db_credentials.json` file should contain the following keys: username (string), password (string), and endpoint (list of strings). You should obtain these details as well as the `certificate.crt` file from your MongoDB admin/setup. 

### Uploading VIRA Content to the Database
The script to upload the content in resources to the db is `db_utils.py`.

To run it, first define the following environment variables: 

1. `BOT_WA_APIKEY`: The API key of the translation service
2. `BOT_WA_URL`: The url of the translation service 
3. `BOT_DASHBOARD_CODE`: The code required to access the evaluation dashboard (currently not active, can be left empty)
4. `BOT_KPA_HOST`: The url of the KPA service in the evaluation dashboard (currently not active, can be left empty)
5. `BOT_KPA_APIKEY`: The API key of the KPA service in the evaluation dashboard (currently not active, can be left empty)
6. `BOT_INTENT_CLASSIFIER_URL`: The url of intent classifier (key-point matching) service of VIRA
7. `BOT_DIALOG_ACT_CLASSIFIER_URL`: The url of the dialog-act service of VIRA

Then run
```shell
python db_utils.py -conf-canned-db
```

## Testing VIRA in Local Environment
1. Define an environment variable 'VIRA_API_KEY'
2. Launch VIRA using ```python main.py```
3. Test VIRA with a simple user question using ```python sanity.py```


## Deploying VIRA in a Containerized Management System
1. Build a docker image using `docker build . -t vira-system`
2. Push the image to a docker registry of choice.
3. Setup a deployment file in which the the files: `db_credentials.json` and `certificate.crt` are mounted to `/app/resources/db/`
4. Deploy the image on your platform using a link to the image on the docker registry. 

## License

If you would like to see the detailed LICENSE click [here](LICENSE).
