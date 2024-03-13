
import argparse
import pyrubberband
import soundfile

def process_audio(input_file, output_file, time_stretch=1.0, pitch_shift=0):
    """
    Processes the audio file to apply time-stretching and pitch-shifting.

    Parameters:
    - input_file: Path to the input WAV file.
    - output_file: Path to save the processed WAV file.
    - time_stretch: Time stretch factor (1.0 for no change).
    - pitch_shift: Pitch shift in semitones (0 for no change).
    """
    # Load audio file
    data, sample_rate = soundfile.read(input_file)
    
    # Apply time-stretching and pitch-shifting
    processed_data = pyrubberband.time_stretch(data, sample_rate, time_stretch)
    processed_data = pyrubberband.pitch_shift(processed_data, sample_rate, pitch_shift)
    
    # Save processed audio file
    soundfile.write(output_file, processed_data, sample_rate)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Time-stretch and pitch-shift a WAV file.")
    parser.add_argument("input_file", type=str, help="Path to the input WAV file.")
    parser.add_argument("output_file", type=str, help="Path to the output WAV file.")
    parser.add_argument("--time_stretch", type=float, default=1.0, help="Time stretch factor. Default is 1.0.")
    parser.add_argument("--pitch_shift", type=int, default=0, help="Pitch shift in semitones. Default is 0.")
    
    args = parser.parse_args()
    
    process_audio(args.input_file, args.output_file, args.time_stretch, args.pitch_shift)
