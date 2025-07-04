import SwiftUI
import RealmSwift
import AVFoundation

// Our observable object class
class RealmSession: ObservableObject {
    var realm: Realm
    
    init() {
       try! FileManager.default.removeItem(at: Realm.Configuration.defaultConfiguration.fileURL!)
        let configuration = Realm.Configuration(deleteRealmIfMigrationNeeded: true)
        realm = try! Realm(configuration: configuration)
     }

}
