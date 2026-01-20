const Mutation = require('../../mutation');

function TDOperator() {
  this.ID = "TD";
  this.name = "timestamp-dependency";
}

TDOperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];

  // Elenco delle proprietà di block con tipo uint
  const uintProperties = new Set([
    'number',
    'timestamp',
    'difficulty',
    'gaslimit',
    'basefee',
    'chainid'
  ]);

  visit({
    MemberAccess: (node) => {
      if (node.expression.type === 'Identifier' && node.expression.name === 'block') {
        const prop = node.memberName;

        // Evita sostituzione di block.timestamp con se stesso
        if (prop !== 'timestamp' && uintProperties.has(prop)) {
          const start = node.range[0];
          const end = node.range[1] + 1;
          const startLine = node.loc.start.line;
          const endLine = node.loc.end.line;
          const original = source.slice(start, end);
          const replacement = "block.timestamp";

          mutations.push(
            new Mutation(
              file,
              start,
              end,
              startLine,
              endLine,
              original,
              replacement,
              this.ID
            )
          );
        }
      }
    }
  });

  return mutations;
};

module.exports = TDOperator;
