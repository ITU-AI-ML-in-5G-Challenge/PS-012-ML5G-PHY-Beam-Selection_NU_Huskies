import os
import numpy as np
import pickle
import random

import keras
from keras.models import Sequential
from keras.layers import Input, Conv2D, MaxPooling2D, Dropout, Flatten, Dense, Activation
from keras import backend as K
from keras.preprocessing.image import load_img
from keras.preprocessing.image import img_to_array
from keras.layers.normalization import BatchNormalization
from keras.optimizers import Adam
from keras.models import Model
from keras.callbacks import ModelCheckpoint
from keras.models import model_from_json

from PIL import Image
from keras.preprocessing.image import load_img
from keras.preprocessing.image import img_to_array
from keras.preprocessing.image import ImageDataGenerator
import time
from collections import Counter
from create_crops_of_Entire_Image import *

def show_all_files_in_directory(input_path):
    'This function reads the path of all files in directory input_path'
    files_list=[]
    for path, subdirs, files in os.walk(input_path):
        for file in files:
            if file.endswith(".png"):
               files_list.append(os.path.join(path, file))
    return files_list



def check_and_create(dir_path):
    if os.path.exists(dir_path):
        return True
    else:
        os.makedirs(dir_path)
        return False




def get_models(model_flag = 'seperate', inputshape=(40,40,3), classes=4, lr=0.001):
    """
    Create original classification model
    """

    model = Sequential()
    # first set of CONV => RELU => POOL layers
    model.add(Conv2D(20, (15,15), padding="same",
        input_shape=inputshape))
    model.add(Activation("relu"))
    model.add(MaxPooling2D(pool_size=(3, 3),strides=(2, 2)))
    model.add(Dropout(0.25))

    model.add(Flatten())
    model.add(Dense(128))
    model.add(Activation("relu"))
    model.add(Dropout(0.5))

    model.add(Dense(classes))
    model.add(Activation("softmax"))

    return model




class TrainTest():
    def __init__(self, base_path = '/home/batool/Directroy/', save_path = '/home/batool/Directroy/'):

        self.model = None
        self.base_path = base_path
        self.save_path = save_path

    def add_model(self, classes, model_flag, model, model_path='/home/batool/Directroy/Wall/model/'):

        self.model = model
        self.classes = classes
        model_json = self.model.to_json()
        print('\n*************** Saving New Model Structure ***************')
        with open(os.path.join(model_path, "model.json"), "w") as json_file:
            json_file.write(model_json)
            print("json file written")


    # loading the model structure from json file
    def load_model_structure(self, classes, model_path='/home/batool/per_batch/Wall/model/homegrown_model.json'):

        # reading model from json file
        json_file = open(model_path, 'r')
        model = model_from_json(json_file.read())
        json_file.close()

        self.model = model
        self.classes = classes

        return model


    def load_weights(self, weight_path = '/home/batool/per_batch/Wall/model/weights.02-3.05.hdf5'):

        self.model.load_weights(weight_path)



    def train_model(self, batch_size, data_path='/home/batool/beam_selection/image/data' , window=50, lr=0.002, epochs=10, model_path = '/home/batool/Directroy/Wall/model/'):
        # Train
        # Create an Image Datagenerator model, and normalize
        traingen = ImageDataGenerator(rescale=1./255, brightness_range=[0.5,1.5])
        train_generator = traingen.flow_from_directory(data_path+'/train/', target_size=(window, window), color_mode="rgb", batch_size=batch_size, class_mode='categorical', shuffle=True)

        batchX, batchy = train_generator.next()
        print('Batch shape=%s, min=%.3f, max=%.3f' % (batchX.shape, batchX.min(), batchX.max()))


        STEP_SIZE_TRAIN = train_generator.n//train_generator.batch_size

        # Validation
        # Create an Image Datagenerator model, and normalize
        valgen = ImageDataGenerator(rescale=1./255, brightness_range=[0.5,1.5])
        validation_generator = valgen.flow_from_directory(data_path+'/validation/', target_size=(window, window), color_mode="rgb", batch_size=batch_size, class_mode='categorical', shuffle=True)

        STEP_SIZE_Validation = validation_generator.n//validation_generator.batch_size


        self.model.compile(loss=keras.losses.categorical_crossentropy, optimizer=Adam(lr=lr), metrics=['accuracy'])
        print('*******************Saving model weights****************')
        self.model.fit_generator(train_generator, steps_per_epoch=STEP_SIZE_TRAIN, validation_data = validation_generator, validation_steps=STEP_SIZE_Validation, epochs=epochs )

        self.model.save_weights(model_path+"model_weights.hdf5")

    def test_model(self, batch_size, data_path='/home/batool/beam_selection/image/data' , window=50, lr=0.002, epochs=10, model_path = '/home/batool/Directroy/Wall/model/'):

        testgen = ImageDataGenerator(rescale=1./255, brightness_range=[0.5,1.5])
        test_generator = testgen.flow_from_directory(data_path+'/test/', target_size=(window, window), color_mode="rgb", batch_size=batch_size,class_mode='categorical',shuffle=True)

        STEP_SIZE_TEST = test_generator.n//test_generator.batch_size

        self.model.compile(loss=keras.losses.categorical_crossentropy, optimizer=Adam(lr=lr), metrics=['accuracy'])
        score = self.model.evaluate_generator(test_generator, steps=STEP_SIZE_TEST, verbose=1)
        print('Test loss:', score[0])
        print('Test accuracy:', score[1])

        label = (test_generator.class_indices)
        self.labels = dict((v,k) for k,v in label.items())
        print(self.labels)





    def predict_on_crops(self, entire_images_path, window=50, stride=20):

        # For each image predict ton corps
        for count, each_image_path in enumerate(entire_images_path):

            print('**********Create crops and save to swap**************')
            SWAP = create_crops_of_entire_Image(each_image_path, self.base_path+'swap', window, stride)
            print('**********Create crops is done**************')

            predgen = ImageDataGenerator(rescale=1./255)
            preds_generator = predgen.flow_from_directory(SWAP , target_size=(window, window), color_mode="rgb",batch_size=1, shuffle=False)
            STEP_SIZE_PRED = preds_generator.n//preds_generator.batch_size
            preds_generator.reset()
            pred=self.model.predict_generator(preds_generator, steps=STEP_SIZE_PRED, verbose=1)
            print('one image predicted, the pred shape is {}'.format(pred.shape))


            # flow from directory sweeps the Images alphabitcly, we need to map each prediction to the right one
            print('**********Maping to the right index**************')
            feeding_order = [SWAP+'/'+str(i)+'.png' for i in range(preds_generator.n)]
            feeding_order = sorted(feeding_order)
            pred_correct = np.zeros((preds_generator.n,4),dtype=np.float32)
            for number,value in enumerate(feeding_order):
                right_index = value.split('/')[-1].split('.')[0]
                pred_correct[int(right_index),:] = pred[number,:]


            print(pred_correct)
            votes = np.argmax(pred_correct, axis=1)
            print(votes)
            print(type(votes))
            print(votes.shape)

            vote_shape = np.transpose(votes.reshape(int((960-40)/5)+1,-1))
            print(vote_shape)
            print(vote_shape.shape)

            np.save(self.base_path+'npys/'+each_image_path.split('/')[-1].split('.')[0]+'.npy',vote_shape)

            ######### TO image
            image_to_save = np.zeros((vote_shape.shape[0],vote_shape.shape[1],3),dtype=np.float32)

            for r in range(vote_shape.shape[0]):
                for c in range(vote_shape.shape[1]):
                    if vote_shape[r,c] == 0:
                        #background
                        image_to_save[r,c,:] = (255,255,255)
                    elif vote_shape[r,c] == 1:
                        #bus
                        image_to_save[r,c,:] = (255,0,0)
                    elif vote_shape[r,c] ==2:
                        #car
                        image_to_save[r,c,:] = (255,128,0)
                    elif vote_shape[r,c] ==3:
                        #truck
                        image_to_save[r,c,:] = (51,153,255)

            print(image_to_save)


            image_to_save= image_to_save.astype('uint8')

            name = each_image_path.split('/')[-1]
            img = Image.fromarray(image_to_save,mode='RGB')
            img.save(self.base_path+'prediction/'+ name)
