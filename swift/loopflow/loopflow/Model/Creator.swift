import Foundation
import RealmSwift

final class Creator: Object, ObjectKeyIdentifiable {
    @Persisted(primaryKey: true) var _id: ObjectId
    @Persisted var creationDate = Date()
}
