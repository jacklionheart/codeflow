import Foundation
import AVFoundation
import Combine

class Mix : Playable {
    var audioEngine: AVAudioEngine
    public var track: Track
    var mixerNode: AVAudioMixerNode
    var trackTimePitch: TrackTimePitch
    var parent: AVAudioNode
    var subtrackPlayers: [Playable] = []
    private var cancellables = Set<AnyCancellable>()

    // MARK: - Public Methods
    
    public func play() {
        subtrackPlayers.forEach { $0.play() }
    }
    
    /// Stops a track from playing.
    public func stop() {
        subtrackPlayers.forEach { $0.stop() }
    }

    // MARK: - Initialization
    
    private func subscribeToChanges() {
        let notificationToken = track.thaw()!.observe { [weak self] change in
            switch change {
            case .change(_, let properties): // Correctly access the properties array in the tuple
                for property in properties {
                    if property.name == "volume", let newValue = property.newValue as? Double {
                        // Update the published pitchCents when the property changes
                        DispatchQueue.main.async {
                            self!.mixerNode.outputVolume = Float(newValue)
                        }
                    }

                }
            case .error(let error):
                AppLogger.audio.error("An error occurred: \(error)")
            case .deleted:
                AppLogger.audio.debug("The object was deleted.")
            }
        }

        // Convert the Realm notification token into a Combine cancellable and add it to the set.
        AnyCancellable {
            notificationToken.invalidate()
        }.store(in: &cancellables)
    }
    
    init(_ track: Track, parent: AVAudioNode, audioEngine: AVAudioEngine) {
        self.track = track
        self.parent = parent
        self.audioEngine = audioEngine
        mixerNode = AVAudioMixerNode()
        mixerNode.outputVolume = Float(track.volume)
        trackTimePitch = TrackTimePitch(track, parent: parent, audioEngine: audioEngine)
        audioEngine.attach(mixerNode)

        track.subtracks.forEach { subtrack in
            subtrackPlayers.append(TrackPlayer.Create(subtrack, parent: mixerNode, audioEngine: audioEngine))
        }
        
        audioEngine.connect(mixerNode, to: trackTimePitch.timePitchNode, format: track.format())

        subscribeToChanges()
    }
    
    deinit {
        // Cancel all subscriptions when this object is being deinitialized
        cancellables.forEach { $0.cancel() }
        audioEngine.detach(mixerNode)
    }
}
