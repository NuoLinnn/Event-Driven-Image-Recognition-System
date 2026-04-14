import redis
import upload_image

# Using REDIS:
r = redis.Redis(host='localhost', port=6379, db=0)

# Create a function to listen for the upload image to have a value returned
def process_image_ready(stream_name):
    last_id = '0'
    while True:
        # Make a 5 sec block in the read stream to add new data
        response = r.xread({stream_name: last_id}, count = 1, block=5000)
        
        if response:
            for stream, messages in response:
                # Set image processing code here
                


    # Send information to either the annotation service or the embedding service
    return
