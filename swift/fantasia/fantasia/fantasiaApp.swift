//
//  fantasiaApp.swift
//  fantasia
//
//  Created by Jack Heart on 11/18/22.
//

import SwiftUI

@main
struct fantasiaApp: App {
    var session = Session()

    var body: some Scene {
        WindowGroup {
            Fantasia().environmentObject(session)
        }
    }
}
