import SwiftUI
import RealmSwift
import AVFoundation

struct PlayerView: View {
    @EnvironmentObject var session: RealmSession
    @EnvironmentObject var audio: Audio
    @ObservedRealmObject var track: Track
    @ObservedObject var trackAudio: TrackAudio
    @State private var expanded = false
    var onEdit: () -> Void

    var body: some View {
        VStack(alignment: .leading) {
            Text(track.name)
                .font(.title).bold().padding(.leading)
            HStack {
                Text(Format.date(track.creationDate))
                Spacer()
                Text(Format.duration(track.durationSeconds))
            }.foregroundColor(.gray)
            HStack {
                PlayButton(trackAudio: trackAudio, track: track)
                Spacer()
                Button(action: {
                    onEdit()
                }) {
                    Image(systemName: "plus")
                        .font(.system(size: 20))
                        .foregroundColor(.blue)
                }.buttonStyle(PlainButtonStyle())
            }
        }
    }
}
