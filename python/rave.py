import torch
import librosa as li
import soundfile as sf
import argparse
import numpy as np

parser = argparse.ArgumentParser(description='Example python script to generate & manipulate audio with RAVE.')
parser.add_argument('--model', type=str, help='The model file (needs non-streaming model?)')
parser.add_argument('--input', type=str, help='Input wav (please pre-convert with ffmpeg)')
parser.add_argument('--output', type=str, default="<<unset>>", help='Default = [input]_out.wav')
parser.add_argument('--duration', type=float, default=9000001.0, help='Cap input wav length')
args = parser.parse_args()

if not (args.model and args.input):
    parser.error('Needs more arguments.')
if args.output == "<<unset>>":
    args.output = args.input+"_out.wav"

def process_audio():
    print("Loading model...")
    torch.set_grad_enabled(False)
    model = torch.jit.load(args.model).eval()
    print("Model loaded successfully")
    print("Model type:", type(model))
    print("Model attributes:", dir(model))

    print("Loading and processing audio...")
    try:
        x, sr = li.load(args.input, sr=44100, duration=args.duration)
    except Exception as e:
        print(f"Error loading audio: {e}")
        return

    print(f"Audio loaded. Shape: {x.shape}, Sample rate: {sr}")

    # Ensure x is a 3D tensor: (batch_size, channels, time)
    if x.ndim == 1:
        x = x.reshape(1, 1, -1)  # mono audio
    elif x.ndim == 2:
        x = x.T.reshape(1, x.shape[1], -1)  # stereo audio
    x = torch.from_numpy(x).float()  # Ensure float32 dtype

    print(f"Input tensor shape: {x.shape}")

    try:
        print("Encoding audio...")
        z = model.encode(x)
        print(f"Encoded shape: {z.shape}")

        print("Decoding audio...")
        y = model.decode(z)
        print(f"Decoded shape: {y.shape}")

        # Reshape output
        y = y.detach().cpu().numpy().reshape(-1, y.shape[1])

        print(f"Writing output to {args.output}...")
        sf.write(args.output, y, sr)
        print("Processing complete!")
    except Exception as e:
        print(f"Error during processing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    process_audio()