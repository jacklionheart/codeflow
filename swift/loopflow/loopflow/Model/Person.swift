import Foundation
import RealmSwift

final class Person: Object, ObjectKeyIdentifiable {
    @Persisted(primaryKey: true) var _id: ObjectId
    @Persisted var creationDate = Date()
}
