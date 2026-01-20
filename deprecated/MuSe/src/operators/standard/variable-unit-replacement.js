const Mutation = require('../../mutation');

/**
 * VUROperator is a mutation testing operator designed to replace units in numeric literals within Solidity code.
 * 
 * **Purpose**:
 * The operator focuses on replacing different units of measurement (like Ether and time units) in numeric literals to assess how such changes affect the contract's functionality. This helps test how robust the contract is against modifications in unit representations.
 * 
 * **How It Works**:
 * 1. **Identify Number Literals**: The script searches for numeric literals with specific units.
 * 2. **Perform Replacements**:
 *    - **Ether Units Replacement**: Replaces Ether units with other units (e.g., `wei` with `ether`, `gwei` with `wei`, etc.).
 *    - **Time Units Replacement**: Replaces time units with other units (e.g., `seconds` with `minutes`, `hours`, `days`, `weeks`, etc.).
 * 3. **Create Mutation Instances**: It creates and records mutations reflecting these unit replacements.
 * 4. **Return Mutations**: The list of mutations is returned for testing and further analysis.
 */

function VUROperator() {
  this.ID = "VUR";
  this.name = "variable-unit-replacement";
}

VUROperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];
  var prevRange;

  visit({
    NumberLiteral: (node) => {
      if (node.subdenomination) {
        if (prevRange != node.range) {
          const start = node.range[0];
          const end = node.range[1] + 1;
          const lineStart = node.loc.start.line;
          const lineEnd = node.loc.end.line;
          const original = source.slice(start, end);
          let replacement;

          switch (node.subdenomination) {
            // Ether Units Replacement
            case 'wei':
              replacement = original.replace('wei', 'ether');
              mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, replacement, this.ID));
              break;
            case 'gwei':
              replacement = original.replace('gwei', 'wei');
              mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, replacement, this.ID));
              break;
            case 'finney':
              replacement = original.replace('finney', 'wei');
              mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, replacement, this.ID));
              break;
            case 'szabo':
              replacement = original.replace('szabo', 'wei');
              mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, replacement, this.ID));
              break;
            case 'ether':
              replacement = original.replace('ether', 'wei');
              mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, replacement, this.ID));
              break;
            // Time Units Replacement
            case 'seconds':
              mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, original.replace('seconds', 'minutes'), this.ID));
              mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, original.replace('seconds', 'hours'), this.ID));
              mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, original.replace('seconds', 'days'), this.ID));
              mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, original.replace('seconds', 'weeks'), this.ID));
              break;
            case 'minutes':
              mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, original.replace('minutes', 'seconds'), this.ID));
              mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, original.replace('minutes', 'hours'), this.ID));
              mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, original.replace('minutes', 'days'), this.ID));
              mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, original.replace('minutes', 'weeks'), this.ID));
              break;
            case 'hours':
              mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, original.replace('hours', 'seconds'), this.ID));
              mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, original.replace('hours', 'minutes'), this.ID));
              mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, original.replace('hours', 'days'), this.ID));
              mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, original.replace('hours', 'weeks'), this.ID));
              break;
            case 'days':
              mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, original.replace('days', 'seconds'), this.ID));
              mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, original.replace('days', 'minutes'), this.ID));
              mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, original.replace('days', 'hours'), this.ID));
              mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, original.replace('days', 'weeks'), this.ID));
              break;
            case 'weeks':
              mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, original.replace('weeks', 'seconds'), this.ID));
              mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, original.replace('weeks', 'minutes'), this.ID));
              mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, original.replace('weeks', 'hours'), this.ID));
              mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, original.replace('weeks', 'days'), this.ID));
              break;
            case 'years':
              mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, original.replace('years', 'seconds'), this.ID));
              mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, original.replace('years', 'minutes'), this.ID));
              mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, original.replace('years', 'hours'), this.ID));
              mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, original.replace('years', 'days'), this.ID));
              mutations.push(new Mutation(file, start, end, lineStart, lineEnd, original, original.replace('years', 'weeks'), this.ID));
              break;
          }
        }
        prevRange = node.range;
      }
    }
  });

  return mutations;
};

module.exports = VUROperator;
