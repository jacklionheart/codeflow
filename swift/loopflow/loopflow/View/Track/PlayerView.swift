import SwiftUI
import RealmSwift
import AVFoundation

struct PlayerView: View {
@EnvironmentObject var session: RealmSession
@ObservedObject var player: Player
@ObservedRealmObject var track: Track
@State private var expanded = false
var onEdit: () -> Void

var body: some View {
    VStack(alignment: .leading) {
        Text(track.name).bold()
        HStack {
            Text(Format.date(track.creationDate))
            Spacer()
            Text(Format.duration(track.durationSeconds))
        }.foregroundColor(.gray)
            HStack {
                PlayButton(player: player, track: track)
                Spacer()
                Button(action: {
                    onEdit()
                }) {
                    Image(systemName: "plus")
                        .font(.system(size: 20))
                        .foregroundColor(.blue)
                }
            }
        }
    }
}
