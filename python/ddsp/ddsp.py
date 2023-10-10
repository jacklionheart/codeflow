# Ignore a bunch of deprecation warnings
import warnings
warnings.filterwarnings("ignore")

import time

import ddsp
from ddsp.training import (data, decoders, encoders, models, preprocessing, 
                           train_util, trainers) 
from ddsp.colab.colab_utils import play, specplot, DEFAULT_SAMPLE_RATE
import gin
import matplotlib.pyplot as plt
import numpy as np
import tensorflow.compat.v2 as tf
import tensorflow_datasets as tfds

sample_rate = DEFAULT_SAMPLE_RATE  # 16000

# Get a single example from NSynth.
# Takes a few seconds to load from GCS.
data_provider = data.NSynthTfds(split='test')
dataset = data_provider.get_batch(batch_size=1, shuffle=False).take(1).repeat()
batch = next(iter(dataset))
audio = batch['audio']
n_samples = audio.shape[1]

specplot(audio)
play(audio)
     