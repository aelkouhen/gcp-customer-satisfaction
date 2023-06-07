# Customer Satisfaction Monitoring with Redis & GCP
Real-Time Customer Satisfaction Monitoring using Redis Enterprise and GCP services. Bellow is the overall architecture:
![customer-satisfaction](https://github.com/aelkouhen/gcp-customer-satisfaction/assets/customer-satisfaction.png)

## Redis Enterprise Setup
First you need to create a Redis Enterprise Cluster. For this, you can use [Terrmaine](https://github.com/amineelkouhen/terramine) project to provision it.
Once your cluster is created, you have to create a database with the following modules activated: Redis Bloom, Redis TimeSeries, Redis JSON, and RediSearch.
Let's assume the database endpoint is `redis-12000.cluster.redis-satisfaction.demo.redislabs.com:12000`

## Google Cloud Setup

1. You need to create a Pub/Sub topic called `customer-satisfaction`. Once the topic is created, click on the `Trigger Cloud Function` button.
![image](https://github.com/aelkouhen/gcp-customer-satisfaction/assets/1-satisfaction.png)

2. Select a 2nd Generation function and name it `function-customer-satisfaction`, then choose your default region (in which the topic and the Redis Cluster are created).
<img width="569" alt="image" src="https://github.com/aelkouhen/gcp-customer-satisfaction/assets/2-satisfaction.png">

3. To simplify the demo, allow unauthenticated invocations and make sure the fucntion is triggered by the right pub/sub topic.
<img width="569" alt="image" src="https://github.com/aelkouhen/gcp-customer-satisfaction/assets/3-satisfaction.png">

4. In the setting, ensure that you allow at least 8GiB of Memory and 2 vCPU for this cloud function.
<img width="546" alt="image" src="https://github.com/aelkouhen/gcp-customer-satisfaction/assets/4-satisfaction.png">

5. Then create three runtime environment variables: `REDIS_HOST`, `REDIS_PORT`, and `REDIS_PWD` with the specific values of your Redis database.
<img width="546" alt="image" src="https://github.com/aelkouhen/gcp-customer-satisfaction/assets/5-satisfaction.png">

6. Finally, copy the content of this [cloud function](https://raw.githubusercontent.com/aelkouhen/gcp-customer-satisfaction/main/cloud-function/main.py) and this [requirements file](https://github.com/aelkouhen/gcp-customer-satisfaction/blob/main/cloud-function/requirements.txt) in the inline editor and click on `deploy function`
<img width="546" alt="image" src="https://github.com/aelkouhen/gcp-customer-satisfaction/assets/6-satisfaction.png">

## Local Setup
1. Install GCloud (see [here](https://cloud.google.com/sdk/docs/install)) 
2. After you install the gcloud CLI, perform initial setup tasks by running gcloud init. You can also run `gcloud init` to change your settings or create a new configuration.
3. Install a few PIP packages:
  - Run `pip install pyaudio` to install pyaudio.  PyAudio provides Python bindings for PortAudio v19, the cross-platform audio I/O library. With PyAudio, you can easily use Python to play and record audio on a variety of platforms, such as GNU/Linux, Microsoft Windows, and Apple macOS.
  - Run `pip install --upgrade google-cloud-speech` to install the Speech-to-Text SDK from Google Cloud. This library converts speech into text with a Google Cloud API.
  - Run `pip install --upgrade google-cloud-pubsub` to install the Pub/Sub SDK from Google Cloud. Pub/Sub ingests incoming events from local machines and triggers a cloud function in GCP.
4. Run this [python program](https://raw.githubusercontent.com/aelkouhen/gcp-customer-satisfaction/main/local-machine/mic_simple.py) locally: `python3 mic_simple.py -customerID <CUSTOMER-REF>`  

## Dashboard Setup

When you use the Terramine project a bastion host is created containing Grafana. From the project output look for this `rs-grafana-endpoint = "http://<BASTION_IP>:3000"` 

In your navigator, enter the url and login to Grafana as admin/admin. Feel free to skip changing the default Grafana password. 
![image](https://github.com/Redislabs-Solution-Architects/aws-fraud-detection/blob/main/docs/images/1-grafana-login.png?raw=true)

Next, go to the settings and add a Data source. Look for Redis and enable it. 
![image](https://github.com/Redislabs-Solution-Architects/aws-fraud-detection/blob/main/docs/images/2-grafana-data-sources.png?raw=true)

Then fill your database endpoint and configured with appropriate password and hit "Save and Test" button. 
![image](https://github.com/Redislabs-Solution-Architects/aws-fraud-detection/blob/main/docs/images/5-grafana-redis-datasource-test.png?raw=true)

Now, you can go to the browse menu and import these two dashboards:
1. The first one is the [Customer Satisfaction Dashboard](https://raw.githubusercontent.com/aelkouhen/gcp-customer-satisfaction/main/dashboards/Customer%20Satisfaction.json) that allows monitoring in Real-Time each incoming call (customer).
![Satisfaction_Customer](https://github.com/aelkouhen/gcp-customer-satisfaction/assets/105490765/adfb2651-aea2-45ef-bb45-28ff444f966e)

2. The second one is the [Overview Dashboard](https://raw.githubusercontent.com/aelkouhen/gcp-customer-satisfaction/main/dashboards/Overview.json) that allows monitoring the overall satisfaction if the call center: It makes statistics about all satisfaction scores of all incoming calls.
<img width="1494" alt="Customer_Overall" src="https://github.com/aelkouhen/customer-satisfaction/assets/105490765/f863a4b8-0756-4491-a3d0-0e3964b80c0c">
