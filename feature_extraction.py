import os
import dlib
import csv
import numpy as np
import logging
import cv2

# Path of cropped faces
path_images_from_camera = "data/data_set/"

# Use frontal face detector of Dlib
detector = dlib.get_frontal_face_detector()

# Get face landmarks
predictor = dlib.shape_predictor('D:\Projects\Autometa\data\model\shape_predictor_68_face_landmarks.dat')

# Use Dlib resnet50 model to get 128D face descriptor
face_reco_model = dlib.face_recognition_model_v1('D:\Projects\Autometa\data\model\dlib_face_recognition_resnet_model_v1.dat')

# Return 128D features for a single image
def return_128d_features(path_img):
    img_rd = cv2.imread(path_img)
    
    if img_rd is None:
        logging.warning(f"Failed to load image: {path_img}")
        return None  # Return None if image is not loaded correctly

    faces = detector(img_rd, 1)

    logging.info("%-40s %-20s", " Image with faces detected:", path_img)

    # For photos of faces saved, we need to make sure that we can detect faces from the cropped images
    if len(faces) != 0:
        shape = predictor(img_rd, faces[0])
        face_descriptor = face_reco_model.compute_face_descriptor(img_rd, shape)
        return face_descriptor
    else:
        logging.warning(f"No face detected in image: {path_img}")
        return None

# Function to select the best image (based on successful feature extraction)
def select_best_image(person_folder_path):
    best_image_path = None
    
    photos_list = os.listdir(person_folder_path)
    
    for photo in photos_list:
        photo_path = os.path.join(person_folder_path, photo)
        
        if not os.path.isfile(photo_path):
            continue
        
        # Try to extract features from the image
        features_128d = return_128d_features(photo_path)
        
        if features_128d is not None:
            best_image_path = photo_path
            break  # We take the first valid image (successful extraction)
    
    return best_image_path

# Return the 128D features for the best image of person X
def return_features_mean_personX(path_face_personX):
    best_image_path = select_best_image(path_face_personX)
    
    if best_image_path:
        features_128d = return_128d_features(best_image_path)
        if features_128d is not None:
            return features_128d
    return np.zeros(128)  # Return zero vector if no valid image is found

def main():
    logging.basicConfig(level=logging.INFO)
    
    # Get the order of latest person
    person_list = os.listdir(path_images_from_camera)
    person_list.sort()

    # Open the existing CSV file to read the names of already processed persons
    processed_persons = set()
    try:
        with open("data/features_all.csv", "r", newline="") as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if row:  # Ensure row is not empty
                    processed_persons.add(row[0])  # Assuming the first column is the person name
    except FileNotFoundError:
        logging.warning("No previous features file found, starting fresh.")

    # Open the CSV file to append new features (keep it open for the entire operation)
    with open("data/features_all.csv", "a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        logging.info("Opened CSV file for writing.")
        
        # List to store the names of persons whose features were not extracted
        persons_without_features = []

        # Iterate through each person and extract features
        for person in person_list:
            person_folder_path = os.path.join(path_images_from_camera, person)
            
            if not os.path.isdir(person_folder_path):
                logging.warning(f"Skipping invalid folder: {person_folder_path}")
                continue
            
            # Skip person if already processed
            if person in processed_persons:
                logging.info(f"Skipping already processed person: {person}")
                continue
            
            # Get the 128D features of face/personX using the best image
            logging.info("Processing person: %s", person)
            features_mean_personX = return_features_mean_personX(person_folder_path)

            if np.array_equal(features_mean_personX, np.zeros(128)):
                # If no valid features were extracted, add person to the list
                persons_without_features.append(person)
                logging.warning(f"Failed to extract features for {person}")
                continue

            # Extract person name (if available)
            person_name = person.split('(')[0].strip()  # Extract name before '('
            
            # Convert _dlib_pybind11.vector to a list, then insert person name
            features_mean_personX = list(features_mean_personX)  # Convert to list
            
            # Insert person name as the first element in the feature vector (129D)
            features_mean_personX.insert(0, person_name)

            # Write the features to the main CSV file
            writer.writerow(features_mean_personX)
            logging.info(f"Features saved for {person_name} in features_all.csv")
        
        # After writing to the main CSV, save individual person files
        for person in person_list:
            person_folder_path = os.path.join(path_images_from_camera, person)
            if os.path.isdir(person_folder_path):
                person_name = person.split('(')[0].strip()
                features_file_path = os.path.join(person_folder_path, f"{person_name}_features.csv")
                try:
                    # Save the features for the person in their respective folder
                    with open(features_file_path, 'w', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow([person_name] + list(features_mean_personX[1:]))  # Skip the first element (person name)
                    logging.info(f"Saved features for {person_name} in {features_file_path}")
                except Exception as e:
                    logging.error(f"Error saving features for {person_name}: {str(e)}")

    # Print the names of the persons whose features were not extracted
    if persons_without_features:
        print("The following persons had no features extracted:")
        for person in persons_without_features:
            print(person)

    logging.info("All new features saved successfully.")

if __name__ == '__main__':
    main()