# Event-Driven-Image-Recognition-System
<img width="1231" height="703" alt="image" src="https://github.com/user-attachments/assets/625d9687-aac1-4c88-96c7-8ea53589ec77" />

## Modules
### CLI Service
The CLI service interacts with the user requests from the command line and sends asynchronous messaging based on what the user input may be.
### Upload Image
The upload image module allows a user to upload their image to the system. This can be the first step towards annotating and embedding the image.
### Annotate Image
The annotate image module
### Embed Image
The embed image module uses vectors and a connection to the vector database to save several sets of information about the image. The first 
### Process Image
The process image module confirms that the image was uploaded, annotated, and embedded and can therefore be considered fully processed. It will return a success message to the user once it recieves success messages for all of these modules for a given image id.
### Query Service
The query service will take user questions and input and return images with similar values. For the sample data in this project, the user can query for images that also have cats or also have dogs in them, and the system will return other uploaded images with cats or dogs.
## Sample Data
### Uploaded Images
The sample images uploaded to this project are two dog images and two cat images. They can be seen here, identified by their image ids.
image_id = dogs13
<img width="1024" height="558" alt="dogs13" src="https://github.com/user-attachments/assets/9d5dee13-e922-4836-94d2-20add792caec" />

image_id = dogs1
<img width="900" height="600" alt="dogs1" src="https://github.com/user-attachments/assets/a665d9fb-025a-4736-8b94-46a7577cfa49" />

image_id = cats2
<img width="277" height="182" alt="cats2" src="https://github.com/user-attachments/assets/8d1a0741-78e6-4f56-924c-46377d7f5e37" />

image_id = cats3
<img width="1600" height="900" alt="cats3" src="https://github.com/user-attachments/assets/eb0a10d1-6b06-44c6-a29d-ac8ed06cd746" />

### Annotated Images
The annotated versions of each image can be seen here, so that a user can identify how many cats or dogs exist in a single image and their locations, using the locations of the boxes.
image_id = dogs13
<img width="1024" height="558" alt="annotated_dogs" src="https://github.com/user-attachments/assets/2b2712a1-651b-4460-9663-a3dfc5abc6ca" />

image_id = dogs1
<img width="900" height="600" alt="annotated_dogs1" src="https://github.com/user-attachments/assets/711cbe73-fa76-4dc8-b83d-f724af77c4c8" />

image_id = cats2
<img width="277" height="182" alt="annotated_cats2" src="https://github.com/user-attachments/assets/7c3ca373-cf5d-4c25-9304-b2164a599103" />

image_id = cats3
<img width="1600" height="900" alt="annotated_cats3" src="https://github.com/user-attachments/assets/f15b32d7-fb43-4b63-8de9-715776911282" />

