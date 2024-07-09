import RealmSwift

class RealmConfiguration {
    static let shared = RealmConfiguration()

    private init() {}

    func configure() {
        let config = Realm.Configuration(
            schemaVersion: 1,
            migrationBlock: { migration, oldSchemaVersion in
                // Perform any necessary migrations here
            }
        )
        Realm.Configuration.defaultConfiguration = config
    }
}
