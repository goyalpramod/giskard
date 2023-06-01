import tensorflow as tf
from tensorflow import keras

from giskard import TensorFlowModel, Dataset

import tests.utils


# Define a simple sequential model
def create_model():
    model = tf.keras.Sequential([
        keras.layers.Dense(512, activation='relu', input_shape=(784,)),
        keras.layers.Dropout(0.2),
        keras.layers.Dense(10, activation='softmax')
    ])

    model.compile(optimizer='adam',
                  loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
                  metrics=[tf.keras.metrics.SparseCategoricalAccuracy()])

    return model


def test_mnist():

    (train_images, train_labels), (_, _) = tf.keras.datasets.mnist.load_data()

    train_labels = train_labels[:100]

    train_images = train_images[:100].reshape(-1, 28 * 28) / 255.0

    # Create and train a new model instance.
    model = create_model()
    model.fit(train_images, train_labels, epochs=1)

    my_model = TensorFlowModel(name="TensorFlow_MNIST",
                               clf=model,
                               model_type="classification",
                               classification_labels=['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'])

    my_test_dataset = Dataset(train_images, name="dataset")

    tests.utils.verify_model_upload(my_model, my_test_dataset)