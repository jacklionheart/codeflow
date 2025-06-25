import Foundation
import RealmSwift
import AVFoundation

class Recorder : ObservableObject {
    var engine: AVAudioEngine
    public var playerRegistry: PlayerRegistry

    private var avAudioRecorder: AVAudioRecorder?
    @Published var currentRecordingPath: URL?
    @Published var currentPitch: Pitch?
    @Published public var name: String
    @Published var elapsedTime: TimeInterval
    private var pitchEstimator: PitchEstimator
    private var startTime: Date?
    private var timer: Timer?

    init(engine: AVAudioEngine, playerRegistry: PlayerRegistry) {
        self.engine = engine
        self.playerRegistry = playerRegistry
        pitchEstimator = PitchEstimator()
        avAudioRecorder = nil
        name = ""
        currentRecordingPath = nil
        currentRecordingPath = nil
        currentPitch = nil
        timer = nil
        startTime = nil
        elapsedTime = 0
    }

    
    func startMonitoring() {
        print("startMonitoring Current thread: \(Thread.current.isMainThread ? "Main" : "Background")")

        let input = engine.inputNode
        let format = input.inputFormat(forBus: 0)
        
        print("inputFormat: \(input.inputFormat(forBus: 0))")
        print("outputFormat: \(input.outputFormat(forBus: 0))")
        AppLogger.audio.debug("record.start installing tap")
        input.installTap(onBus: 0, bufferSize: UInt32(pitchEstimator.minimumSamplesSize()), format: format) { buffer , _ in
            self.currentPitch = self.pitchEstimator.estimate(buffer)
        }
    }

    func stopMonitoring() {
        print("stopMonitoring Current thread: \(Thread.current.isMainThread ? "Main" : "Background")")


        engine.inputNode.removeTap(onBus: 0)
    }
    
    private static func newUrl(for date: Date) -> URL {
        let dateFormatter = DateFormatter()
        dateFormatter.dateFormat = "yyyyMMdd_HHmmss"
        return Track.fileDirectory().appendingPathComponent("Loopflow_Recording_\(dateFormatter.string(from: date)).m4a")
    }
    
    var active: Bool {
        return avAudioRecorder != nil
    }
    
    func start() {
        print("start Current thread: \(Thread.current.isMainThread ? "Main" : "Background")")


        let settings = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 44100,
            AVNumberOfChannelsKey: 2,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
        ]
        
        AppLogger.audio.debug("audio.record.start active:\(self.active)")
        if !active {
            do {
                let date = Date()
                print("start Current thread: \(Thread.current.isMainThread ? "Main" : "Background")")
                currentRecordingPath = Recorder.newUrl(for: date)
                avAudioRecorder = try AVAudioRecorder.init(url: currentRecordingPath!, settings: settings)
                startTime = Date()
                avAudioRecorder!.record()
                startMonitoring()
                elapsedTime = 0
                timer = Timer.scheduledTimer(withTimeInterval: 0.02, repeats: true) { [weak self] _ in
                    self?.updateElapsedTime()
                }
                name = Object.randomName()
                AppLogger.audio.debug("audio.record.start recording to \(self.currentRecordingPath!.absoluteString) active:\(self.active)")
            } catch let error {
                AppLogger.audio.error("audio.record.start Error starting recorder: \(error.localizedDescription)")
                avAudioRecorder = nil
                
                print("start Current thread: \(Thread.current.isMainThread ? "Main" : "Background")")
                currentRecordingPath = nil
            }
        }
    }
    
    func stop(to: Section?) {
        print("stop Current thread: \(Thread.current.isMainThread ? "Main" : "Background")")


        AppLogger.audio.info("audio.record.stop active:\(self.active) to:\(to)")
        if active {
            avAudioRecorder!.stop()
            stopMonitoring()
            playerRegistry.stopCurrent()
            timer = nil
            startTime = nil
            elapsedTime = 0
            do {
                let fileManager = FileManager.default
                let attributes = try fileManager.attributesOfItem(atPath: currentRecordingPath!.path)
                if let fileSize = attributes[.size] as? NSNumber {
                    AppLogger.audio.info("audio.record.stop File size: \(fileSize) bytes")
                } else {
                    AppLogger.audio.error("audio.record.stop Could not retrieve file size.")
                }
            } catch {
                AppLogger.audio.error("audio.record.stop Error getting \(self.currentRecordingPath!.absoluteString) file attributes: \(error.localizedDescription)")
            }
            
            avAudioRecorder = nil
            
            writeToRealm {
                // TODO: Get realm from session?
                let realm = try! Realm()

                let newTrack = Track(name: self.name, sourceURL: self.currentRecordingPath!.lastPathComponent)
                realm.add(newTrack)

                var section = to
                if to == nil {
                    section = Section(name: name + " Section")
                    realm.add(section!)
                }
                
                section!.thaw()!.addTrack(newTrack)
            }
            
            print("stop Current thread: \(Thread.current.isMainThread ? "Main" : "Background")")
            currentRecordingPath = nil
        }
    }
    
    private func updateElapsedTime() {
          guard let startTime = startTime else { return }
          elapsedTime = Date().timeIntervalSince(startTime)
   }
}
