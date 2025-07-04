//
//  RealmTesting.swift
//  fantasiaTests
//
//  Created by Jack Heart on 6/25/24.
//

import Foundation
import XCTest
import RealmSwift

class RealmTesting {
    static func createInMemoryRealm() -> Realm {
        let configuration = Realm.Configuration(
            inMemoryIdentifier: "TestRealm"
        )
        
        do {
            return try Realm(configuration: configuration)
        } catch {
            fatalError("Failed to create in-memory Realm: \(error)")
        }
    }
    
    static func cleanUpRealm(_ realm: Realm) {
        try? realm.write {
            realm.deleteAll()
        }
    }
}
