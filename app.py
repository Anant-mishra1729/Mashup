# Flask application
from flask import Flask
from flask import render_template
from flask import request
from mashup import YoutubeAudioAPI, AudioMashup
import youtube_dl
import smtplib
from flask import jsonify
import os
# Import message library
from email.message import EmailMessage

youtube = YoutubeAudioAPI()

app = Flask(__name__)

results = None
email_id = None
duration = None

@app.route("/")
# Get index.html from templates folder
def index():
    return render_template("index.html", title="Mashup")


# Get data from form
@app.route("/data", methods=["POST"])
def data():
    global results, email_id, duration
    if request.method == "POST":
        query = request.form["name"]
        email_id = request.form["email"]
        max_results = int(request.form["max_results"])
        duration = int(request.form["duration"])

        # Checking if arguments are valid
        if not all([query, email_id, max_results, duration]):
            return render_template(
                "index.html",
                title="Mashup",
                msg="Please provide all the details",
            )

        # Searching
        results = youtube.search(query=query, max_results=max_results, verbose= False)

        results["index"] = results.index.to_list()
        print(results.head())
        return render_template(
            "data.html",
            title = "Select songs to download",
            column_names=results.columns.values,
            row_data=list(results.values.tolist())
        )


@app.route("/mashup", methods=["POST"])
def mashup():
    global results, email_id, duration
    if request.method == "POST":
        # Get all checkboxes
        checkboxes = request.form.getlist("selected")
        # Get all indexes of selected checkboxes
        indexes = [int(i) for i in checkboxes]
        
        # Downloading
        files = youtube.download(indexes)

        # Generating mashup
        mashup = AudioMashup(files, duration= duration, keep=True, output="mashup.mp3")
        mashup.generateMashup(overwrite=True)

        # Sending email
        sendMail()

        return render_template(
            "download.html",
            column_names=results.columns.values,
            row_data=list(results.values.tolist()),
            msg= f"Mashup generated successfully\nsent to {email_id}",
            email_id = email_id,
            title = "Mashup generated successfully"
        )
    
# Function to email the mashup.mp3 file
def sendMail():
    global email_id
    sender_email = os.environ.get("EMAIL_USER")
    sender_password = os.environ.get("EMAIL_PASS")
    receiver_email = email_id

    msg = EmailMessage()
    msg["Subject"] = "Mashup"
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg.set_content("Mashup")

    with open("mashup.mp3", "rb") as f:
        file_data = f.read()
        file_name = f.name

    msg.add_attachment(file_data, maintype="audio", subtype="mp3", filename=file_name)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender_email, sender_password)
        smtp.send_message(msg)


def webDownload(index_list=[]):
    global results
    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "outtmpl": "%(title)s.%(ext)s",
        "noplaylist": True,
        "quiet": True,
    }
    

    # Checking if index_list contains valid indexes
    if not all([index in range(0, len(results)) for index in index_list]):
        raise ValueError("Please provide valid indexes")

    if len(index_list) == 0:
        index_list = results.index
    
    # List of urls to download
    urls = results["urls"][index_list].to_list()

    print(urls)
    # Extract info from urls to allow downloading from client side
    jsonified = []
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        for url in urls:
            info = ydl.extract_info(url, download=False)
            jsonified.append(jsonify(info))
    return jsonified

# Run the app
if __name__ == "__main__":
    app.run(debug=True)
