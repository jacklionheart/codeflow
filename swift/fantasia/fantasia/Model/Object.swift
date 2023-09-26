//
//  Object.swift
//  fantasia
//
//  Created by Jack Heart on 4/19/23.
//
//  Extends RealmSwift's Object with Loopflow-specific functionality
//  and provides a namespace for the Model external API.

import Foundation
import RealmSwift


// Helper functions used internally within the model module.
extension Object {
    // Returns a random name for an object (e.g. Track)
    private static let randomAdjectives = [
        "Stanky", "Funky", "Deep", "Bluesy", "Country", "Hip", "Gnarly", "Groovin'", "Ephemeral", "Organic", "Ambient",
    ]
    private static let randomInstruments = [
        "cello", "vocal", "piano", "guitar", "bass", "synth", "ukelele", "mandolin", "violin", "sax", "trumpet",
    ]
    private static let randomAnimals = [
        "whale", "shark", "turtle", "rhino", "ostrich", "gorilla", "starfish", "sea horse", "urchin", "tuna", "platypus", "eagle", "wolf", "lion", "tiger"
    ]
    static func randomName() -> String {
        return "\(randomAdjectives.randomElement()!) \(randomInstruments.randomElement()!) \(randomAnimals.randomElement()!)"
    }
}

func transaction(_ f: () -> Void) {
    let realm = try! Realm()
    try! realm.write {
        f()
    }
}
