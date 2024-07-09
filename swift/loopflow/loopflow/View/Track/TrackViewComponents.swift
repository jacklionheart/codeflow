import SwiftUI
import RealmSwift

struct VolumeSlider: View {
    @ObservedRealmObject var track: Track
    @EnvironmentObject var session: RealmSession
    
    var body: some View {
        Slider(value: Binding(
            get: { Float(track.volume) },
            set: { newValue in
                AppLogger.ui.debug("VolumeSlider.updateVolume \(track.name): \(newValue)")
                writeToRealm {
                    track.thaw()!.volume = Double(newValue)
                }
            }
        ), in: 0.0...1.0, step: 0.05)
        .padding()
    }
}

struct PitchSlider: View {
    @ObservedRealmObject var track: Track
    @EnvironmentObject var session: RealmSession
    
    var body: some View {
        Slider(value: Binding(
            get: { Float(track.pitchCents) },
            set: { newValue in
                AppLogger.ui.debug("PitchSlider.updatePitch \(track.name): \(newValue)")
                writeToRealm {
                    track.thaw()!.pitchCents = Double(newValue)
                }
            }
        ), in: -1200...1200, step: 100)
        .padding()
    }
}

struct PlayButton: View {
    @EnvironmentObject var audio: Audio
    @ObservedObject var trackAudio: TrackAudio
    @ObservedRealmObject var track: Track
    
    var body: some View {
        Button(action: {
            if trackAudio.isPlaying {
                AppLogger.ui.debug("PlayerView PlayButton pause: \(track.name)")
                audio.pause()
            } else {
                AppLogger.ui.debug("PlayerView PlayButton start: \(track.name)")
                audio.play(trackAudio)
            }
        }) {
            Image(systemName: trackAudio.isPlaying ? "pause.fill" : "play.fill")
                .font(.system(size: 40))
                .foregroundColor(.blue)
        }.buttonStyle(PlainButtonStyle())
    }
}
