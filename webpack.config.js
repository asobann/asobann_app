const path = require('path');

module.exports = {
  entry: './src/js/play_session.js',
  output: {
    path: path.resolve('./src/asobann/app/static'),
    filename: 'main.js',
  },
};
