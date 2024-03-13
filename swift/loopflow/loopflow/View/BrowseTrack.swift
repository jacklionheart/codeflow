import SwiftUI
import RealmSwift
import AVFoundation

struct BrowseTrack: View {
    @EnvironmentObject var session: RealmSession
    @EnvironmentObject var audioMixer: AudioMixer
    @ObservedRealmObject var track: Track
    @Binding var selected: Track?

    func isSelected() -> Bool {
        if selected == nil {
            return false
        }
        return selected! == track
    }
    
    func select() {
        selected = track
    }
    func shiftPitch(up: Bool) {
        let shiftAmount = up ? 1 : -1
        
        let newShift = track.semitoneShift + shiftAmount
        audioMixer.shiftPitch(of: track, by: track.semitoneShift)
        
        writeToRealm {
            track.semitoneShift.wrappedValue = newShift
        }
    }
    
    var body: some View {
        VStack {
            HStack {
//                Text(track.name).onTapGesture {
//                    select()
//                }
                Spacer()
                PlayButton(isPlaying: audioMixer.isPlaying(track), start: {
                    print("playing")
                    audioMixer.play(track)
                    select()
                }, stop: {
                    audioMixer.stop(track)
                })
                Spacer()

                // Display current semitone shift
                Text("\(track.semitoneShift, specifier: "%+.1f") semitones")
                    .foregroundColor(.gray)
                    .font(.system(size: 14))
                // Pitch Shift Buttons
                Group {
                    Image(systemName: "minus")
                        .font(.system(size: 20))
                        .foregroundColor(.blue)
                        .padding([.leading, .trailing], 10)
                        .onTapGesture { shiftPitch(up: false) }
                    Image(systemName: "plus")
                        .font(.system(size: 20))
                        .foregroundColor(.blue)
                        .padding([.leading, .trailing], 10)
                        .onTapGesture { shiftPitch(up: true) }
                }
            }.padding(.leading, 10)
        }
        if isSelected() {
            TrackWaveform(track:track)
        }
    }
    
    
    struct PlayButton: View {
        var isPlaying: Bool
        var start: (() -> Void)
        var stop: (() -> Void)
        
        var body: some View {
            Button(action: {
                if isPlaying {
                    stop()
                } else {
                    start()
                }
            }) {
                Image(systemName: isPlaying ? "pause.fill" : "play.fill")
                    .font(.system(size: 40))
                    .foregroundColor(.blue)
            }
        }
    }
}


