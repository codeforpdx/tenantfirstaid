# Project Containerization Needs and Design

## Context and Problem Statement

While moving towards a more scalable solution for
building, deploying, and hosting Tenant First Aid, we
need a method for deterministic builds, and
deployments that can easily scale by bringing up
identically performing service instances.

## Decision Drivers

* Builds for all parts of Tenant First Aid should be easy
    to generate requiring as few commands as possible
* Build assets should be in a format that is easy to
    consume by cloud services

## Considered Options Front End
* Static FE assets built through GH actions and deployed
    to a GCP Storage Bucket with CDN
* Full front end deployed as a GCP Cloud Run Node.JS app
* Continue deploying full app to a VM

## Considered Options Back End
* Flask app deployed natively by gcloud api's cloud run
    deploy function
* Flask app built agnostically, published to Artifact
    Registry directly, served by Cloud Run
* Continue deploying full app to a VM

## Considered Options Utility Scripts
* Run RAG generation script manually & locally
* Run RAG generation script in GH actions on change
* Deploy RAG generation script as Cloud Function

## Decision Outcome

Chosen option: "{title of option 1}", because {justification. e.g., only option, which meets k.o. criterion decision driver | which resolves force {force} | … | comes out best (see below)}.

<!-- This is an optional element. Feel free to remove. -->
### Consequences

* Good, because {positive consequence, e.g., improvement of one or more desired qualities, …}
* Bad, because {negative consequence, e.g., compromising one or more desired qualities, …}
* … <!-- numbers of consequences can vary -->

## Pros and Cons of the Options Front End

### Static FE assets built through GH actions and deployed to a GCP Storage Bucket with CDN

If we expose the different parts of our app through GCP
Application Load Balancer, then we will get easy
integration with Cloud CDN (https://cloud.google.com/load-balancing/docs/load-balancing-overview).
The front end doesn't require any server side compute
and so the simplest and likely cheapest method would be
to transpile/build the front end in GH actions and deploy
the public assets generated from the build into a Cloud
Storage bucket. GCP buckets can be enabled for CDN serving
which can reduce the overall retrieval cost of frequently
served assets.

* Good, because likely the cheapest solution
* Bad, because more GCP infrastructure to track

### Full front end deployed as a GCP Cloud Run Node.JS app

Similar to how the app is currently deployed via a Node app,
we can generate and publish a Node.JS based server for
providing the front end app.

* Good, because this will use similar architecture as BE if
    we go with the Cloud Run deploy option for the flask app
* Bad, because this option costs more
* Bad, because there is no actual benefit to hosting a
    Node.js server just to serve static assets.

### Continue deploying full app to a VM

* Good, because this requires no additional work from current
    process
* Bad, because this does not allow for the same level of
    scalability as other considered options
* Bad, because this is likely the most expensive option


## Pros and Cons of the Options Back End

### Flask app deployed natively by gcloud api's cloud run deploy function

GCP's cli has some pretty handy built in functionality for
building and deploying python apps directly to Cloud Run (https://cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-service).
This builds and deploys the app in most likely a pretty
compact format using a GCP native image as its base.
These images do get deployed to an associated Artifact
Registry so it should be available to easily spawn
additional Cloud Run services with the same image
if necessary, such as for a staging/deployment
environment.

* Good, because this will likely build the smallest image
    required for serving the flask app as a Cloud Run
    service
* Bad, because this will most likely not generate an image
    that is runnable locally

### Flask app built agnostically, published to Artifact Registry directly, served by Cloud Run

As opposed to the previous option, this would entail
us or GH actions generating a docker/OCI image using
a lightweight image base such as python:alpine. Alpine
based images are normally as minimal as you can get while
still containing your required runtime. This image should
run the same locally as in the cloud. Once built, the image
would be deployed to an Artifact Registry, and then served
from a Cloud Run instance.

* Good, because we should get the same behavior of this
    image regardless of whether running locally or in the
    cloud
* Bad, because it might possibly be a slightly larger image
    size than the previous option resulting in a slight cost
    increase which should be minimal but worth noting

### Continue deploying full app to a VM

* Good, because it's already done!
* Bad, because it's probably the most expensive option
