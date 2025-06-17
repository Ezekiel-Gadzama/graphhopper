package com.graphhopper.http;

import com.graphhopper.GraphHopper;
import com.graphhopper.routing.ev.*;
import com.graphhopper.routing.util.EncodingManager;
import com.graphhopper.routing.util.OSMParsers;
import com.graphhopper.routing.util.parsers.OSMIDTagParser;
import com.graphhopper.routing.weighting.custom.NameValidator;
import com.graphhopper.routing.weighting.custom.ValueExpressionVisitor;
import com.graphhopper.util.PMap;
import java.util.List;
import java.util.Map;

public class CustomGraphHopper extends GraphHopper {

    @Override
    protected EncodingManager buildEncodingManager(
            Map<String, PMap> encodedValuesWithProps,
            Map<String, ImportUnit> activeImportUnits,
            Map<String, List<String>> restrictionVehicleTypesByProfile) {

        // Only add OSM ID encoding if it's not already present
        if (!activeImportUnits.containsKey(OSMIDTagParser.KEY)) {
            // 1. Register OSM ID as an import unit using the factory method
            activeImportUnits.put(OSMIDTagParser.KEY, ImportUnit.create(
                    OSMIDTagParser.KEY,
                    p -> {
                        String bitsStr = p.getString("bits", "31");
                        String storeTwoStr = p.getString("store_two_directions", "false");

                        int bits = Integer.parseInt(bitsStr);
                        boolean storeTwoDirections = Boolean.parseBoolean(storeTwoStr);
                        return new IntEncodedValueImpl(OSMIDTagParser.KEY, bits, storeTwoDirections);
                    },
                    null, // No tag parser needed for OSM IDs
                    new String[0] // No required import units
            ));

            // 2. Add configuration
            PMap osmIdProps = new PMap();
            osmIdProps.putObject("bits", "31");
            osmIdProps.putObject("store_two_directions", "false");
            encodedValuesWithProps.put(OSMIDTagParser.KEY, osmIdProps);
        }

        // 3. Handle car profile
        encodedValuesWithProps.putIfAbsent("car", new PMap());

        return super.buildEncodingManager(encodedValuesWithProps, activeImportUnits, restrictionVehicleTypesByProfile);
    }

    @Override
    protected OSMParsers buildOSMParsers(
            Map<String, PMap> encodedValuesWithProps,
            Map<String, ImportUnit> activeImportUnits,
            Map<String, List<String>> restrictionVehicleTypesByProfile,
            List<String> ignoredHighways) {

        OSMParsers osmParsers = super.buildOSMParsers(
                encodedValuesWithProps, activeImportUnits, restrictionVehicleTypesByProfile, ignoredHighways);

        // Only add the parser if the encoding exists
        if (getEncodingManager().hasEncodedValue(OSMIDTagParser.KEY)) {
            osmParsers.addWayTagParser(new OSMIDTagParser(getEncodingManager()));
        }

        return osmParsers;
    }
}
