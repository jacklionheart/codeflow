import SwiftUI
import RealmSwift
import AVFoundation

struct PlayerView: View {
    @EnvironmentObject var session: RealmSession
    @EnvironmentObject var audio: Audio
    @ObservedObject var player: Player
    
    var body: some View {
        VStack(alignment: .leading) {
            Text(player.loop.name)
                .font(.title).bold().padding(.leading)
            HStack {
                Text(Format.date(player.loop.creationDate))
                Spacer()
                Text(Format.duration(player.loop.durationSeconds))
            }.foregroundColor(.gray)
            HStack {
                PlayButton(player: player)
                }.buttonStyle(PlainButtonStyle())
            }
        ScrollableWaveformView(player: player, loop: player.loop)
//        GlobalWaveformView(trackPlayer: player, loop: player.loop)
    }

    
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
        @ObservedObject var player : Player
        
        var body: some View {
            Button(action: {
                if player.isPlaying {
                    AppLogger.ui.debug("PlayerView PlayButton pause: \(player.loop.name)")
                    player.pause()
                } else {
                    AppLogger.ui.debug("PlayerView PlayButton start: \(player.loop.name)")
                    player.play()
                }
            }) {
                Image(systemName: player.isPlaying ? "pause.fill" : "play.fill")
                    .font(.system(size: 40))
                    .foregroundColor(.blue)
            }.buttonStyle(PlainButtonStyle())
        }
    }
}

