import gradio as gr
from PIL import Image
import numpy as np
import random
import webuiapi
from webuiapi.webuiapi import ControlNetUnit as c_unit
import requests
from io import BytesIO
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import base64
import os


def get_files_list(base_url, bearer_token, path):
    # Make the GET request to get the list of files in the specified path
    headers = {'Authorization': f'Bearer {bearer_token}'}
    params = {'path': path}

    api_url = base_url + '/api/2.0/dbfs/list'

    response = requests.get(api_url, headers=headers, params=params)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the JSON response
        json_data = response.json()
        # Filter out only the non-directory files
        files_list = [file['path'] for file in json_data.get('files', []) if not file.get('is_dir', False)]
        return files_list
    else:
        # Handle the case where the request fails
        print(f"Failed to get files list. Status code: {response.status_code}")
        print("Response:", response.text)
        return []

def send_email(recipient_email, base_url, bearer_token, user_id):
    # Set up the MIME objects
    msg = MIMEMultipart()
    msg['From'] = "usman.zubair@databricks.com"
    msg['To'] = recipient_email
    msg['Subject'] = "NRF Databricks PuppyBot Test"

    # Attach the message to the email
    msg.attach(MIMEText("this is a test email", 'plain'))

    # Get list of files in user directory
    user_dir = '/demos/retail/puppybot/' + user_id

    
    files_list = get_files_list(base_url, bearer_token, user_dir)

    if (len(files_list)) == 0:
         return "Please enter a valid UserId!"
    
    # input_image = download_image(base_url, bearer_token, download_path)
    # # return input_image

    # # Decode base64 image data
    # decoded_image_data = base64.b64decode(input_image)

    # # Attach the image to the email
    # image_attachment = MIMEImage(decoded_image_data)
    # image_attachment.add_header('Content-Disposition', 'attachment', filename='image.jpg')
    # msg.attach(image_attachment)

    # Iterate over the .jpg files in the list
    for file_path in files_list:
        # Make the GET request to get the file content
        response = download_image(base_url, bearer_token, file_path)
           
        # Decode base64 image data
        decoded_image_data = base64.b64decode(response)

        # Attach the file to the email
        file_attachment = MIMEImage(decoded_image_data)
        file_attachment.add_header('Content-Disposition', 'attachment', filename=file_path.split('/')[-1])
        msg.attach(file_attachment)

    try:
        # Establish a connection to the SMTP server (Gmail in this case)
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            # Start the TLS connection
            server.starttls()

            # Log in to the sender's Gmail account
            email_password = os.environ.get("email_password")
            server.login("usman.zubair@databricks.com", email_password)

            # Send the email
            server.sendmail("usman.zubair@databricks.com", recipient_email, msg.as_string())

        return "Email sent successfully!"
    except Exception as e:
        return "Email FAILED!" + f"Error: {e}"

def encode_image_to_base64(image_pil):
    # Convert PIL.Image to bytes
    image_bytes = BytesIO()
    image_pil.save(image_bytes, format='JPEG')  # You may need to adjust the format based on your image type

    # Encode the bytes to base64
    encoded_image = base64.b64encode(image_bytes.getvalue()).decode('utf-8')

    return encoded_image

def upload_image(base_url, image_pil, bearer_token, upload_path):
    try:
        # Encode image to base64
        encoded_image = encode_image_to_base64(image_pil)

        # Prepare the headers with Bearer Token
        headers = {'Authorization': f'Bearer {bearer_token}'}

        # Prepare the JSON payload for the POST request
        payload = {
            "path": upload_path,
            "contents": encoded_image, #base64
            "overwrite": "true"
        }

        # Make the POST request with headers and data
        api_url = base_url + '/api/2.0/dbfs/put'
        response = requests.post(api_url, json=payload, headers=headers)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            print("Image uploaded successfully!")
            print("Response:", response.json())
        else:
            print(f"Failed to upload image. Status code: {response.status_code}")
            print("Response:", response.text)
    except Exception as e:
        print(f"Error: {e}")

def download_image(base_url, bearer_token, path):
    try:

        # Prepare the parameters for the GET request
        params = {'path': path}

        # Prepare the headers with Bearer Token
        headers = {'Authorization': f'Bearer {bearer_token}'}

        # Make the POST request with headers and data
        api_url = base_url + '/api/2.0/dbfs/read'
        response = requests.get(api_url, params=params, headers=headers)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Parse the JSON response
            json_data = response.json()
            
            # Return the 'data' element
            return json_data.get('data', '')
        else:
            print(f"Failed to download image. Status code: {response.status_code}")
            print("Response:", response.text)
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None


# Define a function to calls the PuppyBot API service
def call_puppyBot_interrogate(tunnel_url, api_path, image_pil):

    api = webuiapi.WebUIApi(baseurl=f"{tunnel_url}{api_path}",
                        sampler='Euler a',
                        steps=20)
    
    
    captioning = api.interrogate(image=image_pil, model="deepdanbooru").info

    return captioning

# Define a function to calls the PuppyBot API service
def call_puppyBot(tunnel_url, api_path, image_pil, text_input):

    api = webuiapi.WebUIApi(baseurl=f"{tunnel_url}{api_path}",
                        sampler='Euler a',
                        steps=20)
    
    prompt = "show me this dog running through a " + text_input
    
    negative_prompt = "drawing, painting, crayon, sketch, graphite, impressionist, noisy, blurry, soft, deformed, ugly, out of frame, illustration, art, sketch"

    
    cunit_1 = c_unit(image_pil, module="ip-adapter_clip_sd15", model="ip-adapter_sd15 [6a3f6166]", pixel_perfect=True)
    cunit_2 = c_unit(image_pil, module="reference_only", pixel_perfect=True)
    cunit_3 = c_unit(image_pil, module="depth_leres++", pixel_perfect=True)
    
    result1 = api.img2img(controlnet_units=[cunit_1, cunit_2, cunit_3],
      images=[image_pil],
      denoising_strength=0.75,
      prompt=prompt,
      seed=-1,
      n_iter=1,
      cfg_scale=7.0,
      width=512,
      height=512,
      negative_prompt=negative_prompt,
      eta=1.0,
      send_images=True,
      save_images=True,
      use_deprecated_controlnet=False,
      use_async=False)

    return result1.image

# This functions takes the image input, handles the prompts and passes them to the api_method
def process_input(image_in, prompts, user_id):

    base_url = 'https://e2-demo-field-eng.cloud.databricks.com'
    bearer_token = os.environ.get("env_token")
    counter = 1

    tunnel_url = "https://93f3-35-155-15-56.ngrok-free.app"
    api_path = "/sdapi/v1"

    #input validation
    if not image_in.any():
        raise gr.Error("Please upload a picture or take a picture using your camera!")

    if not prompts:
            raise gr.Error("Please select at least 1 prompt!")
    
    if user_id == "":
            raise gr.Error("Please enter a unique User ID or Name!")

    image_response_list = []

    image_pil = Image.fromarray(image_in)
    
    #save the input image to dbfs
    upload_image(base_url, image_pil, bearer_token, '/demos/retail/puppybot/' + user_id + '/source.jpg')

    for prompt in prompts:

        api_response_image = call_puppyBot(tunnel_url, api_path, image_pil, prompt)

        #save the generated image to dbfs
        upload_image(base_url, api_response_image, bearer_token, '/demos/retail/puppybot/' + user_id + '/output_' + str(counter) + '.jpg')

        image_response_list.append(np.array(api_response_image))

        counter = counter + 1

    caption = call_puppyBot_interrogate(tunnel_url, api_path, image_pil)

    return image_response_list, caption


def process_email_request(email, user_id):

    base_url = 'https://e2-demo-field-eng.cloud.databricks.com'
    bearer_token = os.environ.get("env_token")
    counter = 1
  
    if email == "":
            raise gr.Error("Please enter a valid Email Address!")
    
    if user_id == "":
            raise gr.Error("Please enter a unique User ID or Name!")

    email_response = send_email(email, base_url, bearer_token, user_id)

    return email_response


# Define the Gradio interface with a button to capture the image
with gr.Blocks() as blocks:
  
    gr.Markdown("### Puppy Bot powered by Databricks AI""")
    
    image_from_cam = gr.Image(sources=['webcam','upload'])
    
    prompts = gr.CheckboxGroup(["Beach", "Sunset", "Park"], label="Locations")

    user_id = gr.Textbox("", info = "Unique identifier for user (no spaces)", label = "User Id")
    
    submit_btn = gr.Button("Submit")

    #output = gr.Textbox(label="Output Box")

    img_desc = gr.Textbox("", label="Input Image Caption")

    image_out =gr.Gallery(object_fit="contain", height="auto")
    
    submit_btn.click(fn=process_input, inputs=[image_from_cam,prompts, user_id], outputs=[image_out, img_desc], api_name="puppyBot")

    email_address = gr.Textbox("", label = "Email")

    email_btn = gr.Button("Email")

    email_out = gr.Textbox("", label="Email Status")

    email_btn.click(fn=process_email_request, inputs=[email_address, user_id], outputs=[email_out], api_name="puppyBot")

    



# # Customize the CSS to change the appearance further (optional)
# iface.css("""
#     body {
#         font-family: Arial, sans-serif;
#     }
#     .gr-interface {
#         max-width: 800px;
#         margin: 0 auto;
#     }
# """)

# Launch the Gradio interface
if __name__ == "__main__":
    blocks.launch(show_api=False,share=True)   