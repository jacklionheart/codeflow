//
//  PitchTests.swift
//  loopflow
//
//  Created by Jack Heart on 7/11/24.
//

import Foundation
import XCTest
@testable import loopflow

class PitchTests: XCTestCase {
    
    func testInitWithHz() {
        let pitch = Pitch(440)
        XCTAssertEqual(pitch.hz, 440)
        XCTAssertEqual(pitch.noteName, .A)
        XCTAssertEqual(pitch.octave, 4)
        XCTAssertLessThan(abs(pitch.cents), 0.01) // Should be very close to 0
    }
    
    func testInitWithMidiNoteNumber() {
        let pitch = Pitch(midiNoteNumber: 69) // A4
        XCTAssertEqual(pitch.midiNoteNumber, 69)
        XCTAssertEqual(pitch.noteName, .A)
        XCTAssertEqual(pitch.octave, 4)
        XCTAssertLessThan(abs(pitch.hz - 440), 0.01) // Should be very close to 440 Hz
    }
    
    func testInitWithNoteNameAndOctave() {
        let pitch = Pitch(noteName: .C, octave: 4)
        XCTAssertEqual(pitch.noteName, .C)
        XCTAssertEqual(pitch.octave, 4)
        XCTAssertLessThan(abs(pitch.hz - 261.63), 0.01) // C4 should be close to 261.63 Hz
    }
    
    func testFullName() {
        let pitch = Pitch(noteName: .FSharp, octave: 3)
        XCTAssertEqual(pitch.fullName, "F♯3")
    }
    
    func testFlatName() {
        XCTAssertEqual(Pitch.NoteName.CSharp.flatName, "D♭")
        XCTAssertEqual(Pitch.NoteName.F.flatName, "F")
    }
    
    func testComparison() {
        let lowerPitch = Pitch(440)
        let higherPitch = Pitch(880)
        XCTAssertLessThan(lowerPitch, higherPitch)
    }
    
    func testNearestPitch() {
        let nearestPitch = Pitch(445)
        XCTAssertEqual(nearestPitch.noteName, .A)
        XCTAssertEqual(nearestPitch.octave, 4)
    }
    
    func testCentsCalculation() {
        let sharpPitch = Pitch(445) // Slightly sharp A4
        XCTAssertGreaterThan(sharpPitch.cents, 0)
        XCTAssertLessThan(sharpPitch.cents, 20)
        
        let flatPitch = Pitch(435) // Slightly flat A4
        XCTAssertLessThan(flatPitch.cents, 0)
        XCTAssertGreaterThan(flatPitch.cents, -20)
    }
}
