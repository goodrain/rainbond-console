import React, {Fragment} from 'react';
//美洽 
export default class Meiqia extends React.PureComponent {
    componentDidMount(){
        (function(m, ei, q, i, a, j, s) {
            m[a] = m[a] || function() {
                (m[a].a = m[a].a || []).push(arguments)
          };
            j = ei.createElement(q),
                s = ei.getElementsByTagName(q)[0];
            j.async = true;
            j.charset = 'UTF-8';
            j.src = i;
            s.parentNode.insertBefore(j, s)
        })(window, document, 'script', '//eco-api.meiqia.com/dist/meiqia.js', '_MEIQIA');
        _MEIQIA('entId', 5732);
    }
    render(){
        return null;
    }
}