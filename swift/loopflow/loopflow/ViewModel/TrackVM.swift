import Foundation

class TrackViewModel: ObservableObject {
    @Published var track: Track // Your track model
    @Published var playbackRate: Float = 1.0
    @Published var volume: Float = 1.0

    init(track: Track) {
        self.track = track
    }

    func shiftPitch(up: Bool) {
        let shiftAmount = up ? 100.00 : -100.00
        let newShift = track.pitchCents + shiftAmount
        writeToRealm {
            track.thaw()!.pitchCents = newShift
        }
    }

    func updateVolume() {
        writeToRealm {
            track.thaw()!.volume = Double(volume)
        }
    }

    func updatePlaybackRate() {
        writeToRealm {
            track.thaw()!.playbackRate = Double(playbackRate)
        }
    }
}

