import SwiftUI
import RealmSwift
import Waveform

struct TimeView: View {
    
    @ObservedRealmObject var track: Track
    
    func audioSamples() -> SampleBuffer {
        // only looking at left channel for now
        return SampleBuffer(samples: track.audioFile().floatChannelData()![0])
    }
    
    var body: some View {
        GeometryReader { geometry in
            Waveform(samples: audioSamples()).foregroundColor(.blue).frame(height: 50)
        }
    }
}

