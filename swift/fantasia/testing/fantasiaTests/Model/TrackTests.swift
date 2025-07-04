//
//  TrackTests.swift
//  fantasiaTests
//
//  Created by Jack Heart on 6/25/24.
//

import XCTest
import RealmSwift
@testable import fantasia

final class TrackTests: XCTestCase {
    var realm: Realm!

    override func setUpWithError() throws {
        realm = RealmTesting.createInMemoryRealm()
    }

    override func tearDownWithError() throws {
        RealmTesting.cleanUpRealm(realm)
    }

    func testTrackInitialization() {
        let track = Track(name: "Test Track", sourceURL: "test.mp3")
        
        XCTAssertEqual(track.name, "Test Track")
        XCTAssertEqual(track.sourceURL, "test.mp3")
        XCTAssertEqual(track.subtype, .Recording)
        XCTAssertGreaterThan(track.durationSeconds, 0)
    }
    
    func testConvertToMix() {
        let track = Track(name: "Test Track", sourceURL: "test.mp3")
        
        try! realm.write {
            realm.add(track)
            track.convertToMix()
        }
        
        XCTAssertEqual(track.subtype, .Mix)
        XCTAssertEqual(track.subtracks.count, 1)
        XCTAssertEqual(track.subtracks[0].name, "Test Track")
        XCTAssertEqual(track.subtracks[0].sourceURL, "test.mp3")
        XCTAssertEqual(track.sourceURL, "")
    }
    
    func testAddSubtrack() {
        let parentTrack = Track(name: "Parent Track", sourceURL: "parent.mp3")
        let subTrack = Track(name: "Sub Track", sourceURL: "sub.mp3")
        
        try! realm.write {
            realm.add(parentTrack)
            parentTrack.addSubtrack(subTrack)
        }
        
        XCTAssertEqual(parentTrack.subtype, .Mix)
        XCTAssertEqual(parentTrack.subtracks.count, 1)
        XCTAssertEqual(parentTrack.subtracks[0].name, "Sub Track")
        XCTAssertEqual(subTrack.parent, parentTrack)
    }
    
    func testResetMix() {
        let track = Track(name: "Test Track", sourceURL: "test.mp3")
        track.volume = 0.5
        track.pitchCents = 100
        track.playbackRate = 1.5
        
        try! realm.write {
            realm.add(track)
            track.resetMix()
        }
        
        XCTAssertEqual(track.volume, 1.0)
        XCTAssertEqual(track.pitchCents, 0.0)
        XCTAssertEqual(track.playbackRate, 1.0)
    }
        
//    func testComputeAmplitudes() {
//         // Get the URL of the test audio file
//         guard let audioURL = Bundle(for: type(of: self)).url(forResource: "test_audio", withExtension: "wav") else {
//             XCTFail("Could not find test audio file")
//             return
//         }
//         
//         // Copy the audio file to the documents directory (simulating how it would be in the app)
//         let documentsURL = Track.fileDirectory()
//         let destinationURL = documentsURL.appendingPathComponent("test_audio.wav")
//         
//         do {
//             if FileManager.default.fileExists(atPath: destinationURL.path) {
//                 try FileManager.default.removeItem(at: destinationURL)
//             }
//             try FileManager.default.copyItem(at: audioURL, to: destinationURL)
//         } catch {
//             XCTFail("Failed to copy test audio file: \(error)")
//             return
//         }
//         
//         // Create a track with the test audio
//         let track = Track(name: "Test Track", sourceURL: "test_audio.wav")
//         
//         // Compute amplitudes
//         let amplitudes = track.computeAmplitudes()
//         
//         // Basic checks
//         XCTAssertFalse(amplitudes.isEmpty, "Amplitudes array should not be empty")
//         XCTAssertTrue(amplitudes.allSatisfy { $0 >= 0 }, "All amplitudes should be non-negative")
//         
//         // Check if the number of amplitudes is reasonable
//         // This depends on the length of your test audio file and the samplesPerAmplitude value in the method
//         // Adjust this check based on your specific test audio file
//         XCTAssertGreaterThan(amplitudes.count, 10, "There should be a reasonable number of amplitude values")
//         
//         // You might want to add more specific checks based on the known content of your test audio file
//         // For example, if you know your file has a loud section in the middle:
//         // XCTAssertGreaterThan(amplitudes[amplitudes.count / 2], 0.5, "The middle of the audio should have high amplitude")
//         
//         // Clean up
//         try? FileManager.default.removeItem(at: destinationURL)
//     }
}
