import Foundation
import AVFoundation
import Combine

class Mix : TrackPlayerInternal, ObservableObject {
    // MARK: - Member variables

    // Initialization paramters
    var track: Track
    var audioEngine: AVAudioEngine
    var parent: AVAudioNode

    // Internal implementation
    var mixerNode: AVAudioMixerNode
    var subtrackPlayers: [TrackPlayer] = []

    // MARK: - Public Methods
    
    public func play() {
        subtrackPlayers.forEach { $0.play() }
    }
    
    // Stops a track from playing.
    public func stop() {
        subtrackPlayers.forEach { $0.stop() }
    }
    
    func updateVolume(_ volume : Float) {
        mixerNode.outputVolume = volume
    }
    
    // MARK: - Initialization
    
    init(_ track: Track, parent: AVAudioNode, audioEngine: AVAudioEngine) {
        self.track = track
        self.parent = parent
        self.audioEngine = audioEngine

        mixerNode = AVAudioMixerNode()
        mixerNode.outputVolume = Float(track.volume)
        audioEngine.attach(mixerNode)

        track.subtracks.forEach { subtrack in
            subtrackPlayers.append(TrackPlayer(subtrack, parent: mixerNode, audioEngine: audioEngine))
        }
        audioEngine.connect(mixerNode, to: parent, format: track.format())

    }

    deinit {
        subtrackPlayers = []
        audioEngine.disconnectNodeInput(mixerNode)
        audioEngine.disconnectNodeOutput(mixerNode)
        audioEngine.detach(mixerNode)
    }
}
