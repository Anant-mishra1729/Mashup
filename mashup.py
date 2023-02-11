# Using yoututbesearchpython to get json daya

from youtube_search import YoutubeSearch
import time
import tabulate
import argparse
import youtube_dl
from pydub import AudioSegment
import tqdm
import os
import pandas as pd


class YoutubeAudioAPI:
    def __init__(self):
        self.ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "progress_hooks": [self.show_progress],
            "outtmpl": "%(title)s.%(ext)s",
            "noplaylist": True,
            "quiet": True,
        }


    def show_progress(self, d):
        if d["status"] == "downloading":
            print(
                f"{d['_percent_str']} of {d['_total_bytes_str']} at {d['_speed_str']}",
                end="\r",
            )
        if d["status"] == "finished":
            print("Done downloading, now converting ...")
            yield d
        if d["status"] == "error":
            print(d["error"])

    def _convertViews(self, views):
        # Views are in numbers like 102020886 we need to convert it to 2.1M, 1.2B etc
        if views >= 1000000000:
            return f"{round(views/1000000000, 1)}B"
        elif views >= 1000000:
            return f"{round(views/1000000, 1)}M"
        elif views >= 1000:
            return f"{round(views/1000, 1)}K"
        else:
            return views

    def search(self, query, max_results, verbose=True):
        print("Searching...")
        start = time.time()
        self.results = YoutubeSearch(query, max_results=max_results).to_dict()
        end = time.time()
        print(
            f"Search completed in {round(end-start, 2)} seconds.\nFound {len(self.results)} results.\n"
        )

        self.results = pd.DataFrame(self.results)

        # Drop url_suffix column and create urls column with full url
        self.results["urls"] = self.results["url_suffix"].apply(
            lambda x: f"https://www.youtube.com/{x}"
        )
        self.results.drop("url_suffix", axis=1, inplace=True)

        # Keeping only title, duration, views, url and channel
        self.results = self.results[["title", "duration", "views", "urls", "channel"]]

        # If type of views is string then replace , with empty string, ' views' with empty string and convert to int and sort by views
        self.results["views"] = self.results["views"].apply(
            lambda x: int(
                x.replace(",", "").replace(" views", "") if type(x) == str else x
            )
        )
        self.results.sort_values(by="views", inplace=True, ascending=False)

        # Resetting index
        self.results.reset_index(drop=True, inplace=True)

        # Converting views to 2.1M, 1.2B etc
        self.results["views"] = self.results["views"].apply(self._convertViews)

        # Rename duration to video_duration
        self.results.rename(columns={"duration": "video_duration"}, inplace=True)

        # If verbose is True then print the results
        if verbose:
            print(tabulate.tabulate(self.results, headers="keys", tablefmt="psql"))

        return self.results[['title', 'views', 'channel', 'urls', 'video_duration']]

    def download(self, index_list=[]):
        # Checking if index_list contains valid indexes
        if not all([index in range(0, len(self.results)) for index in index_list]):
            raise ValueError("Please provide valid indexes")

        if len(index_list) == 0:
            index_list = pd["index"]


        filenames = []
        with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
            for url in self.results["urls"][index_list]:
                info = ydl.extract_info(url, download=False)
                # Replace extension with mp3
                filename = os.path.splitext(ydl.prepare_filename(info))[0] + ".mp3"
                filenames.append(filename)
                if os.path.exists(filename):
                    print(f"File {filename} already exists. Skipping...")
                else:
                    print(f"Downloading {filename}...")
                    try:
                        ydl.download([url])
                    except:
                        print("Error occured while downloading. Skipping...")
                        pass
        return filenames


class AudioMashup:
    def __init__(self, audioFiles, output, duration, keep=False):
        self.audioFiles = audioFiles
        self.output = output
        self.duration = duration
        self.keep = keep

    def trimAudio(self, audio, duration):
        # Checking if audio is longer than duration
        if len(audio) > duration * 1000:
            # Trimming audio
            audio = audio[: duration * 1000]
            return audio
        else:
            raise ValueError("Audio is shorter than duration")

    def exportAudio(self, audio, overwrite=False):
        # Check if audio is not empty
        if len(audio) > 0:
            # Saving audio
            if not self.output.endswith(".mp3"):
                self.output += ".mp3"

            if os.path.exists(self.output) and not overwrite:
                print(f"File {self.output} already exists.")
                print("Do you want to overwrite? (y/n)", end=" ")
                choice = input()
                if choice == "y":
                    audio.export(self.output, format="mp3")
            else:
                audio.export(self.output, format="mp3")
            print(f"Saved to {self.output}")
        else:
            raise ValueError("Audio is empty")


    def trimConcat(self, audio):
        # Checking if audio is longer than duration
        if len(audio) > self.duration * 1000:
            # Trimming audio
            audio = audio[: self.duration * 1000]
            return audio
        else:
            raise ValueError("Audio is shorter than duration")


    def generateMashup(self, overwrite=False):
        # Loading audio
        output_audio = AudioSegment.empty()

        # Checking if duration is valid
        if self.duration <= 0:
            raise ValueError("Please provide a valid duration")

        print("\nGenerating mashup...")
        for track in tqdm.tqdm(self.audioFiles):
            try:
                audio = AudioSegment.from_file(track)
            except:
                print(f"Error occured while loading {track}. Skipping...")
                continue

            # Trimming audio
            try:
                audio = self.trimAudio(audio, self.duration)
            except:
                print(f"Error occured while trimming {track}. Skipping...")
                continue
            # Concatenating audio
            try:
                output_audio += audio
            except:
                print(f"Error occured while concatenating {track}. Skipping...")
                continue

        # Exporting audio
        try:
            self.exportAudio(output_audio, overwrite=overwrite)
        except:
            print("Error occured while exporting audio.")
            print("Please check if audio is empty or duration is too long.")

        # Deleting audio files
        if not self.keep:
            for audio in self.audioFiles:
                os.remove(audio)


if __name__ == "__main__":

    # Parsing arguments
    parser = argparse.ArgumentParser(description="Youtube Search API")
    parser.add_argument("-q", "--name", type=str, help="Singer name")
    parser.add_argument(
        "-n",
        "--max_results",
        default=10,
        type=int,
        help="Maximum number of results to return",
    )
    parser.add_argument(
        "-l",
        "--audio_duration",
        help="Audio duration (in seconds) or 00:00:00 (HH:MM:SS) format",
        type=int,
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Output file name (default : date_time.mp3)",
        default=time.strftime("%d_%m_%Y_%H_%M_%S") + ".mp3",
    )
    parser.add_argument(
        "-k",
        "--keep",
        action="store_true",
        help="Keep audio files after concatenation (default : False)",
        default=False,
    )

    args = parser.parse_args()

    # Checking if arguments are valid
    if not args.name:
        raise ValueError("Please provide a singer name")
    if not args.audio_duration:
        raise ValueError("Please provide an audio duration")

    # Converting audio duration to seconds
    if args.audio_duration:
        try:
            args.audio_duration = int(args.audio_duration)
        except:
            args.audio_duration = sum(
                x * int(t)
                for x, t in zip([3600, 60, 1], args.audio_duration.split(":"))
            )


    youtube = YoutubeAudioAPI()

    # Searching
    youtube.search(query=args.name, max_results=args.max_results)

    # If user wants to provide indexes else download all
    print(
        "Choose indexes to download (separated by space) or press enter to download all"
    )
    choice = input()
    if choice:
        indices = [int(index) for index in choice.split()]
    else:
        indices = []

    # Downloading audio
    files = youtube.download(indices)

    # Trimming audio
    mashup = AudioMashup(files, args.output, args.audio_duration, args.keep)
    mashup.generateMashup()
