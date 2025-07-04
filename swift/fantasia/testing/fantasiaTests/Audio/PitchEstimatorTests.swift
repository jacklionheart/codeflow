(1) Teacher signs up, a basic screen with three tabs at bottom:
 - Students: can see all students, and add new students
 - Lessons: can see all lessons, and add new lessons
 - Pieces: can see all pieces, and add new pieces

Students Tab:
 - Simple contacts lists, base on Apple Contacts app. Ideally we can use AirDrop and manual email and/or phone as main ways to add.
 - Require iCloud account or whatever so that user only adds one identifying piece of info and then we bring it as much automaticaly as psosbile 
 - Do whatevers standard for student to "approve" being added

 Lessons:
 This is going to be a bit more complex over time, but for now let's start with one giant list of lessons.
 Each Lesson records whether or not it's been shared with, eventually we'll build better UIs for filtering by student
 Lessons have editable lists of sections, default is two: Warm-ups / Songs
 Each section has a list of Songs, can create new songs or reference any previous song from any other lesson
 Longer term we want to copy lists of warmups and otehr stuff, but e can frget about that for now


Pieces:
Pieces have 4 things right now:
- a PDF of sheet music
- a video recording
- any notes on how to play
- a recommended ammount of time to spend on the Piece

A Piece can be marked as either a warmup or a song.

WE need at least one of the first two. Can start with just the sheet music ad the requiremetn though.
Ideally we can ingest pdfs from as many sources as possible. Pick whateve makes sense as the right place to start. Maybe CloudKit has a library we can use and have the teachers add to elsewehre?


(2) Teacher then adds studentm, pieces, and lessons

(3) Then teacher needs a UI to share a lesson with a student.

(4) For now let's keep the student experience very simple. They only have 1 active lesson at a time, whatever's been shared with them by the teacher.
Students have to have a teacher and can only have one teacher.
The only thing they can do is (1) see an overvie of their lesson and (2) start the lesson

They should then be able to simply navigate through the lesson where each time they lesson shows the main sheet music with teh modules as options, and some button for moving on to next song or goign back to rpevious song.


