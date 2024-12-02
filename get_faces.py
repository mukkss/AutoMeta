import dlib
import numpy as np
import cv2
import os
import shutil
import time
import logging
import tkinter as tk
from tkinter import font as tkFont
from PIL import Image, ImageTk

# Use frontal face detector of Dlib
detector = dlib.get_frontal_face_detector()

class Face_Register:
    def __init__(self):

        self.current_frame_faces_cnt = 0  # cnt for counting faces in current frame
        self.existing_faces_cnt = 0  # cnt for counting saved faces
        self.ss_cnt = 0  # cnt for screen shots

        # Tkinter GUI
        self.win = tk.Tk()
        self.win.title("Face Register")

        # Please modify window size here if needed
        self.win.geometry("1000x500")

        # GUI left part
        self.frame_left_camera = tk.Frame(self.win)
        self.label = tk.Label(self.win)
        self.label.pack(side=tk.LEFT)
        self.frame_left_camera.pack()

        # GUI right part
        self.frame_right_info = tk.Frame(self.win)
        self.label_cnt_face_in_database = tk.Label(self.frame_right_info, text=str(self.existing_faces_cnt))
        self.label_fps_info = tk.Label(self.frame_right_info, text="")
        self.input_name = tk.Entry(self.frame_right_info)
        self.input_usn = tk.Entry(self.frame_right_info)  # Add USN input field
        self.input_name_char = ""
        self.input_usn_char = ""  # Variable for USN input
        self.label_warning = tk.Label(self.frame_right_info)
        self.label_face_cnt = tk.Label(self.frame_right_info, text="Faces in current frame: ")
        self.log_all = tk.Label(self.frame_right_info)

        self.font_title = tkFont.Font(family='Helvetica', size=20, weight='bold')
        self.font_step_title = tkFont.Font(family='Helvetica', size=15, weight='bold')
        self.font_warning = tkFont.Font(family='Helvetica', size=15, weight='bold')

        self.path_photos_from_camera = "data/data_faces_from_camera/"
        self.current_face_dir = ""
        self.font = cv2.FONT_ITALIC

        # Current frame and face ROI position
        self.current_frame = np.ndarray
        self.face_ROI_image = np.ndarray
        self.face_ROI_width_start = 0
        self.face_ROI_height_start = 0
        self.face_ROI_width = 0
        self.face_ROI_height = 0
        self.ww = 0
        self.hh = 0

        self.out_of_range_flag = False
        self.face_folder_created_flag = False

        # FPS
        self.frame_time = 0
        self.frame_start_time = 0
        self.fps = 0
        self.fps_show = 0
        self.start_time = time.time()

        self.cap = cv2.VideoCapture(0)  # Get video stream from camera

    def GUI_get_input_name_usn(self):
        self.input_name_char = self.input_name.get()
        self.input_usn_char = self.input_usn.get()  # Get USN input
        self.create_face_folder()
        self.label_cnt_face_in_database['text'] = str(self.existing_faces_cnt)

    def GUI_info(self):
        tk.Label(self.frame_right_info,
                 text="Face register",
                 font=self.font_title).grid(row=0, column=0, columnspan=3, sticky=tk.W, padx=2, pady=20)

        tk.Label(self.frame_right_info, text="FPS: ").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.label_fps_info.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)

        tk.Label(self.frame_right_info, text="Faces in database: ").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.label_cnt_face_in_database.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)

        tk.Label(self.frame_right_info,
                 text="Faces in current frame: ").grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        self.label_face_cnt.grid(row=3, column=2, columnspan=3, sticky=tk.W, padx=5, pady=2)

        self.label_warning.grid(row=4, column=0, columnspan=3, sticky=tk.W, padx=5, pady=2)

        # Step 1: Input name and create folders for face
        tk.Label(self.frame_right_info,
                 font=self.font_step_title,
                 text="Step 1: Input name and USN").grid(row=7, column=0, columnspan=2, sticky=tk.W, padx=5, pady=20)

        tk.Label(self.frame_right_info, text="Name: ").grid(row=8, column=0, sticky=tk.W, padx=5, pady=0)
        self.input_name.grid(row=8, column=1, sticky=tk.W, padx=0, pady=2)

        tk.Label(self.frame_right_info, text="USN: ").grid(row=9, column=0, sticky=tk.W, padx=5, pady=0)
        self.input_usn.grid(row=9, column=1, sticky=tk.W, padx=0, pady=2)

        tk.Button(self.frame_right_info,
                  text='Input',
                  command=self.GUI_get_input_name_usn).grid(row=9, column=2, padx=5)

        # Step 2: Save current face in frame
        tk.Label(self.frame_right_info,
                 font=self.font_step_title,
                 text="Step 2: Save face image").grid(row=10, column=0, columnspan=2, sticky=tk.W, padx=5, pady=20)

        tk.Button(self.frame_right_info,
                  text='Save current face',
                  command=self.save_current_face).grid(row=11, column=0, columnspan=3, sticky=tk.W)

        # Show log in GUI
        self.log_all.grid(row=12, column=0, columnspan=20, sticky=tk.W, padx=5, pady=20)

        self.frame_right_info.pack()

    def pre_work_mkdir(self):
        # Create folders to save face images and csv
        if not os.path.isdir(self.path_photos_from_camera):
            os.mkdir(self.path_photos_from_camera)

    def check_existing_faces_cnt(self):
        # Check if there are any folders inside the main directory
        if os.listdir(self.path_photos_from_camera):
            # Get a sorted list of folder names
            person_list = os.listdir(self.path_photos_from_camera)
            person_num_list = []
            
            # Iterate over the folder names and try to extract the number from the folder name
            for person in person_list:
                try:
                    # Attempt to split the folder name by '_' and extract the number
                    person_order = person.split('_')[1]  # This assumes the format 'person_x'
                    person_num_list.append(person_order)
                except IndexError:
                    # If the folder name doesn't match the expected format, skip it
                    print(f"Skipping folder with unexpected name: {person}")
                    continue

            # Update the existing faces count based on the number of valid folders
            self.existing_faces_cnt = len(person_num_list)
        else:
            self.existing_faces_cnt = 0

    def update_fps(self):
        now = time.time()
        if str(self.start_time).split(".")[0] != str(now).split(".")[0]:
            self.fps_show = self.fps
        self.start_time = now
        self.frame_time = now - self.frame_start_time
        self.fps = 1.0 / self.frame_time
        self.frame_start_time = now

        self.label_fps_info["text"] = str(self.fps.__round__(2))

    def create_face_folder(self):
        # Create the folders for saving faces
        self.existing_faces_cnt += 1
        if self.input_name_char and self.input_usn_char:
            # Create directory using Name and USN (in format: name(USN))
            self.current_face_dir = os.path.join(self.path_photos_from_camera,
                                                f"{self.input_name_char}({self.input_usn_char})")
            os.makedirs(self.current_face_dir, exist_ok=True)
            self.face_folder_created_flag = True
            self.label_warning.config(text="Ready to save face", font=self.font_warning, fg="green")
        else:
            self.label_warning.config(text="Please input name or USN", font=self.font_warning, fg="red")
            
    def save_current_face(self):
        if self.face_folder_created_flag:
            if self.existing_faces_cnt < 5:  # Limit the number of faces per person to 5
                self.ss_cnt += 1
                current_frame_resized = cv2.resize(self.current_frame, (500, 500))
                # Save image in the format: name_USN_1.jpg (using the counter for each face)
                image_name = f"{self.input_name_char}_{self.input_usn_char}_{self.ss_cnt}.jpg"
                cv2.imwrite(os.path.join(self.current_face_dir, image_name), current_frame_resized)

                self.existing_faces_cnt = len(os.listdir(self.current_face_dir))
                self.label_cnt_face_in_database['text'] = str(self.existing_faces_cnt)
                
                # Success message
                self.label_warning.config(text="Face saved successfully!", font=self.font_warning, fg="green")

                # Optionally clear the success message after a delay
                self.win.after(2000, self.clear_success_message)  # Clear message after 2 seconds
            else:
                self.label_warning.config(text="Maximum of 5 faces reached", font=self.font_warning, fg="red")
        else:
            self.label_warning.config(text="Name and USN must be entered", font=self.font_warning, fg="red")

    def clear_success_message(self):
        # Clear the success message
        self.label_warning.config(text="")

    def process_frame(self):
        # Capture a frame from the camera
        ret, self.current_frame = self.cap.read()
        if not ret:
            return

        # Detect faces in the frame
        gray = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2GRAY)
        faces = detector(gray)

        self.current_frame_faces_cnt = len(faces)

        # Only update the label_face_cnt if it's not in "saving face" state
        if self.ss_cnt == 0:  # This check prevents updates when saving face
            self.label_face_cnt["text"] = "Faces in current frame: " + str(self.current_frame_faces_cnt)

        # Draw rectangles around faces
        for face in faces:
            x, y, w, h = (face.left(), face.top(), face.width(), face.height())
            cv2.rectangle(self.current_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        self.update_fps()

    def run(self):
        self.pre_work_mkdir()
        self.check_existing_faces_cnt()

        self.GUI_info()

        while True:
            self.process_frame()

            # Convert frame to PhotoImage and display in tkinter
            cv2image = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(cv2image)
            imgtk = ImageTk.PhotoImage(image=img)
            self.label.imgtk = imgtk
            self.label.configure(image=imgtk)

            self.win.update()

if __name__ == "__main__":
    face_register = Face_Register()
    face_register.run()
