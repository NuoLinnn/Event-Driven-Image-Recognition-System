# Event-Driven-Image-Recognition-System
## Project Overview
The project uses a combination of modules with asynchronous messaging to build a visual object retrieval system. Users are able to interact with the command line to upload images and query the system for similar images to be returned. The overall system is capable of storing and relating images using the modules shown in this diagram.

<img width="1231" height="703" alt="image" src="https://github.com/user-attachments/assets/625d9687-aac1-4c88-96c7-8ea53589ec77" />

## Modules
### CLI Service
The CLI service interacts with the user requests from the command line and sends asynchronous messaging based on what the user input may be. The CLI service can take two inputs, 'upload an image' or 'query a topic'. When each of these are entered, they call functions that send asynchronous messages to either the upload image or query modules and wait for them to complete. These are the two messages that this module sends, but it also has a Redis listen function that subscribes to the query answered channel and waits for a message there. This ensures that the CLI task completes successfully.

### Upload Image
The upload image module allows a user to upload their image to the system. This can be the first step towards annotating and embedding the image. The module uses Redis to listen for the upload image requested message coming from the CLI service. Once it receives that message, it calls a function within the same module to do the upload image task. Once the upload image task is completed, the image payload is sent to the image uploaded channel.

The actual upload image implementation checks the image extension. It verifies the image extension and path before saving the image payload information in a SQLite database.

### Annotate Image
The annotate image module records the number of individual searchable objects in an image. This module also uses the Redis pub/sub architecture. The listen function listens for a message on the image processing requested channel and ensures the task can be completed, sending a success message when it is. There is also a function that sends a success message to the image annotating channel once the annotation is done.

The actual implementation of the module starts by connecting to Redis and MongoDB, then reads in manually entered data for the sample set of images. The manually read in annotated image data is then added to the image payload and saved to MongoDB.

### Embed Image
The embed image module uses vectors and a connection to the vector database to save several sets of information about the image. There is a Redis listener that listens for a message that the image annotation has been completed, which must happen before the image can be embedded. Once that happens, the embedding can begin. There is also a function to send a Redis message to the image embedded channel once the image embedding is complete.

For the actual image embedding implementation, the module sets up a manual embedding process that works on the test set of images. The primary vector set is the set of "latitude-longitude" coordinates that represent different pets in the database. In the data established so far, dogs are represented by coordinates located in the city of Boston, and cats are represented by coorindates in the city of New York. On this simplified version of the system, a new image could be uploaded and would be assigned city coordiantes based on the pet the image contains. If there are other pets in the system that are part of the same city, they would be assigned to show they are "close" to the newly uploaded image.

### Process Image
The process image module works with several other modules to complete its tasks. Once the processing is requested, the message is sent to the  image processing requested channel. It confirms that the image was uploaded, annotated, and embedded and can therefore be considered fully processed. This module listens for a message from the upload, embed, and annotate image modules before the image is processed. It will return a success message to the user once it recieves success messages for all of these modules for a given image id. 

The actual image processing is done using two functions to process the data from the embedding and annotating modules. Then, another function acquires a Redis lock, merging the image id data with the complete step's data and ensuring that all other modules are complete.

### Query Service
The query service will take user questions and input and return images with similar values. The Redis pub/sub architecture has a listen function that listens for a message on the query requested channel and returns success. Once the query is complete, it sends a message to the query complete channel along with publishing the image payload to the channel.

For the sample data in this project, the user can query for images that also have cats or also have dogs in them, and the system returns a mock input to indicate that the query was received.

## Unit Testing
The majortiy of unit testing used in the project tests the ability of the asynchronous Redis pub/sub messaging system. Each module has a corresponding test module that runs unit tests by creating a mock Redis connection and tests the listen and send functions of each module.

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

## Tech Stack
| Component | Technology |
|-----------|------------|
| Messaging | Redis pub/sub |
| Vector search | FAISS |
| Annotation storage | MongoDB (Motor async driver) |
| Async runtime | Python asyncio |

## Video Overview
https://drive.google.com/file/d/1AfJVF2aa2-62rS3-2VmRJJRgSSm7DKOQ/view?usp=sharing
