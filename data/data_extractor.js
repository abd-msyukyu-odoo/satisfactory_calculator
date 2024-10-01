// https://satisfactory.wiki.gg/wiki/Recipes
// 29/09/2024
// missing energy buildings
// missing minable resources

function resources(node, canvasLength, modifier = -1) {
    const result = []
    let counter = 0;
    for (const item of node.querySelectorAll(".recipe-item")) {
        let name = (item.querySelector(".item-name").textContent).toLowerCase();
        let amount = modifier * parseFloat(item.querySelector(".item-amount").textContent);
        result.push(name, amount);
        counter++;
    }
    for (; counter < canvasLength; counter++) {
        result.push("", "");
    }
    return result.join(",");
}

function compute(target) {
    let aggregate = [];
    let validation = new Set([
        "smelter",
        "foundry",
        "constructor",
        "assembler",
        "manufacturer",
        "packager",
        "refinery",
        "blender",
        "particle accelerator",
        "quantum encoder",
        "converter",
    ]);
    for (let tr of target.querySelectorAll("tr")) {
        let tds = [...tr.querySelectorAll("td")];
        // building
        let building = tds[2].querySelector("a").firstChild.textContent.toLowerCase();
        if (!validation.has(building)) {
            continue;
        }
        // key
        let key = tds[0].firstChild.textContent.toLowerCase();
        // duration
        let brs = [...tds[2].querySelector(".recipe-building").querySelectorAll(":scope > br")];
        let duration = parseFloat(brs.at(0)?.nextSibling?.textContent).toString()
        // custom energy
        let powerNode = tds[2].querySelector(".recipe-energy")?.firstChild.textContent;
        let power = "";
        if (powerNode) {
            let [powerDown, powerUp] = powerNode.replaceAll(",", "").split(" - ").map((power) => {
                return parseFloat(power);
            });
            power = ((powerUp + powerDown) / -2).toString();
        }
        // outputs <=2
        let outputs = resources(tds[3], 2, 1);
        // inputs <=4
        let inputs = resources(tds[1], 4);
        aggregate.push([
            key,
            building,
            duration,
            outputs,
            inputs,
            power
        ].join(","))
    }
    console.log(aggregate.join("\n"));
}

// use the table tbody
compute($0);
