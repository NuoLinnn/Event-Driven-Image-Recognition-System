# Event-Driven-Image-Recognition-System

## Modules
### CLI Service
### Upload Image
### Annotate Image
### Embed Image
The embed image module uses vectors and a connection to the vector database to save several sets of information about the image. The first 
### Process Image
The process image module confirms that the image was uploaded, annotated, and embedded and can therefore be considered fully processed. It will return a success message to the user once it recieves success messages for all of these modules for a given image id.
### Query Service
The query service will take user questions and input and return images with similar values. For the sample data in this project, the user can query for images that also have cats or also have dogs in them, and the system will return other uploaded images with cats or dogs.
