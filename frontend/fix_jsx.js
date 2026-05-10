const fs = require('fs');
const path = require('path');
const file = path.join(__dirname, 'frontend/src/components/NewsroomChatbot.jsx');
let content = fs.readFileSync(file, 'utf-8');

// There are multiple open divs that are not properly closed!
// The return starts on line 236: return (<div className="...">

fs.writeFileSync(file, content);
