//
//  Creator.swift
//  fantasia
//
//  Created by Jack Heart on 4/19/23.
//

import Foundation
import RealmSwift

final class Creator: Object, ObjectKeyIdentifiable {
    @Persisted(primaryKey: true) var _id: ObjectId
    @Persisted var creationDate = Date()
}
