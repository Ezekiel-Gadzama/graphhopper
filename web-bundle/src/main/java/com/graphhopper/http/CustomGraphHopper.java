package com.graphhopper.http;

import com.graphhopper.GraphHopper;
import com.graphhopper.routing.ev.*;
import com.graphhopper.routing.util.EncodingManager;
import com.graphhopper.routing.util.OSMParsers;
import com.graphhopper.routing.util.parsers.OSMIDTagParser;
import com.graphhopper.util.PMap;
import java.util.List;
import java.util.Map;

public class CustomGraphHopper extends GraphHopper {

    @Override
    protected EncodingManager buildEncodingManager(
            Map<String, PMap> encodedValuesWithProps,
            Map<String, ImportUnit> activeImportUnits,
            Map<String, List<String>> restrictionVehicleTypesByProfile) {

        // Create and configure OSM ID properties
        PMap osmIdProps = new PMap();
        osmIdProps.putObject("bits", 31);
        osmIdProps.putObject("store_two_directions", false);

        // Add to the configuration map
        encodedValuesWithProps.put(OSMIDTagParser.KEY, osmIdProps);

        // Ensure car profile is configured
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
