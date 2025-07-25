package com.graphhopper.routing.weighting.custom;

import com.graphhopper.json.Statement;
import com.graphhopper.routing.ev.*;
import com.graphhopper.routing.util.EncodingManager;
import com.graphhopper.routing.weighting.DefaultTurnCostProvider;
import com.graphhopper.routing.weighting.TurnCostProvider;
import com.graphhopper.storage.BaseGraph;
import com.graphhopper.storage.NodeAccess;
import com.graphhopper.util.CustomModel;
import com.graphhopper.util.EdgeIteratorState;
import com.graphhopper.util.PMap;
import com.graphhopper.util.TurnCostsConfig;
import org.junit.jupiter.api.Test;

import java.util.Collections;

import static org.junit.jupiter.api.Assertions.*;

public class CustomWeightingIntegrationTest {

    @Test
    public void testBasicFunctionality() {
        // 1. Define encoded values
        BooleanEncodedValue accessEnc = new SimpleBooleanEncodedValue("car_access", true);
        BooleanEncodedValue roundaboutEnc = new SimpleBooleanEncodedValue("car_roundabout", false);
        DecimalEncodedValue speedEnc = new DecimalEncodedValueImpl("car_speed", 5, 5, true);
        DecimalEncodedValue ferrySpeedEnc = new DecimalEncodedValueImpl("car_ferry_speed", 5, 5, false);
        EnumEncodedValue<RoadClass> roadClassEnc = new EnumEncodedValue<>(RoadClass.KEY, RoadClass.class);

        // For TurnCostProvider
        BooleanEncodedValue turnRestrictionEnc = new SimpleBooleanEncodedValue("car_turn_restriction", false);
        DecimalEncodedValue orientationEnc = new DecimalEncodedValueImpl("orientation", 8, 0, false);

        // 2. Build EncodingManager
        EncodingManager encodingManager = EncodingManager.start()
                .add(accessEnc)
                .add(roundaboutEnc)
                .add(speedEnc)
                .add(ferrySpeedEnc)
                .add(roadClassEnc)
                .add(turnRestrictionEnc)
                .add(orientationEnc)
                .build();

        // 3. Create graph
        BaseGraph graph = new BaseGraph.Builder(encodingManager).create();
        EncodedValueLookup lookup = encodingManager;

        // 4. Create TurnCostProvider
        TurnCostsConfig tcConfig = new TurnCostsConfig(); // use defaults
        TurnCostProvider turnCostProvider = new DefaultTurnCostProvider(turnRestrictionEnc, orientationEnc, graph, tcConfig);

        // 5. Create nodes and edges
        NodeAccess na = graph.getNodeAccess();
        na.setNode(0, 49.1, 11.1);
        na.setNode(1, 49.2, 11.2);
        EdgeIteratorState edge = graph.edge(0, 1).setDistance(1000);
        edge.set(speedEnc, 100.0);
        edge.set(roadClassEnc, RoadClass.MOTORWAY);

        // 6. Create CustomModel
        CustomModel model = new CustomModel()
                .addToPriority(Statement.If("road_class == MOTORWAY", Statement.Op.MULTIPLY, "0.5"))
                .addToSpeed(Statement.If("true", Statement.Op.LIMIT, "car_speed"));

    // Extract both parameters and weighting
        CustomWeighting.Parameters parameters = CustomModelParser.createWeightingParameters(model, lookup);
        CustomWeighting weighting = new CustomWeighting(turnCostProvider, parameters);

    // Now you can directly test speed/priority
        double speed = parameters.getEdgeToSpeedMapping().get(edge, false);
        double priority = parameters.getEdgeToPriorityMapping().get(edge, false);

        assertTrue(speed > 0, "Speed should be positive");
        assertTrue(priority > 0, "Priority should be positive");

        System.out.println("Test passed! Speed: " + speed + ", Priority: " + priority);

    }
}
