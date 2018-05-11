const unitArr = ['KB', 'MB', 'GB', 'TB', 'PB']
const util = {
     unit: (num, baseUnit='KB', fixed=2) => {
         num = Number(num);
         var currUnit = baseUnit;
         var index = unitArr.indexOf(currUnit);
         while(num >= 1024){
             num = num/1024;
             index++;
             currUnit = unitArr[index];
         }
         if(num % 1 === 0){
             return num+' '+currUnit;
         }
         return num.toFixed(2)+' '+currUnit;
     }
}

export default util;