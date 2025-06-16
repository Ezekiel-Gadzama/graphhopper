package com.graphhopper.routing.util.parsers;

import com.graphhopper.reader.ReaderWay;
import com.graphhopper.routing.ev.*;
import com.graphhopper.storage.IntsRef;

public class OSMIDTagParser implements TagParser {

    public static final String KEY = "osm_id";
    private final IntEncodedValue osmIdEnc;

    public OSMIDTagParser(EncodedValueLookup lookup) {
        this.osmIdEnc = lookup.getIntEncodedValue(KEY);
    }

    @Override
    public void handleWayTags(int edgeId, EdgeIntAccess edgeIntAccess, ReaderWay way, IntsRef edgeFlags) {
        int osmId = (int) way.getId();
        osmIdEnc.setInt(false, edgeId, edgeIntAccess, osmId);
    }
}
