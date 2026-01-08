const Mutation = require('../../mutation');

/**
 * SFROperator is a mutation testing operator that focuses on replacing SafeMath function calls with other SafeMath functions.
 * 
 * **Purpose**:
 * This operator generates mutations by replacing SafeMath functions (`add`, `sub`, `mul`, `div`, `mod`) with other SafeMath functions within Solidity contracts. This mutation helps to test if the contract correctly handles arithmetic operations and reacts appropriately to changes in the operation being performed.
 * 
 * **How It Works**:
 * 1. **Identify SafeMath Usage**: The script first checks if the contract imports the SafeMath library.
 * 2. **Find and Replace**: If SafeMath is used, it scans for function calls to SafeMath functions and replaces them with different SafeMath functions.
 * 3. **Generate Mutations**: For each replacement, a mutation is created and stored for further testing.
 */

function SFROperator() {
  this.ID = "SFR";
  this.name = "safemath-function-replacement";
}

SFROperator.prototype.getMutations = function (file, source, visit) {
  const mutations = [];
  var isUsingSafeMath = false;

  // Check if the SafeMath library is imported
  visit({
    ImportDirective: (node) => {
      if (node.path.includes('SafeMath'))
        isUsingSafeMath = true;
    }
  });

  if (isUsingSafeMath) {
    // If SafeMath is used, find and replace SafeMath function calls
    visit({
      MemberAccess: (node) => {
        const start = node.range[0];
        const end = node.range[1] + 1;
        const lineStart = node.loc.start.line;
        const lineEnd = node.loc.end.line;
        const original = source.slice(start, end);

        var replacement, replacement2, replacement3, replacement4;

        switch (node.memberName) {
          case 'add':
            // Replace 'add' with other SafeMath functions
            replacement = original.replace('add', 'sub');
            replacement2 = original.replace('add', 'div');
            replacement3 = original.replace('add', 'mul');
            replacement4 = original.replace('add', 'mod');
            break;
          case 'sub':
            // Replace 'sub' with other SafeMath functions
            replacement = original.replace('sub', 'add');
            replacement2 = original.replace('sub', 'div');
            replacement3 = original.replace('sub', 'mul');
            replacement4 = original.replace('sub', 'mod');
            break;
          case 'mul':
            // Replace 'mul' with other SafeMath functions
            replacement = original.replace('mul', 'add');
            replacement2 = original.replace('mul', 'div');
            replacement3 = original.replace('mul', 'sub');
            replacement4 = original.replace('mul', 'mod');
            break;
          case 'div':
            // Replace 'div' with other SafeMath functions
            replacement = original.replace('div', 'mul');
            replacement2 = original.replace('div', 'add');
            replacement3 = original.replace('div', 'sub');
            replacement4 = original.replace('div', 'mod');
            break;
          case 'mod':
            // Replace 'mod' with other SafeMath functions
            replacement = original.replace('mod', 'mul');
            replacement2 = original.replace('mod', 'add');
            replacement3 = original.replace('mod', 'sub');
            replacement4 = original.replace('mod', 'div');
            break;
        }
        if (replacement) {
          mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, replacement, this.ID));
        }
        if (replacement2) {
          mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, replacement2, this.ID));
        }
        if (replacement3) {
          mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, replacement3, this.ID));
        }
        if (replacement4) {
          mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, replacement4, this.ID));
        }
      }
    });
  }

  return mutations;
}

module.exports = SFROperator;
