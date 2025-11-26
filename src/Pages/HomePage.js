// ForexListPage.jsx
import React from "react";
import {
    Box,
    AppBar,
    Toolbar,
    IconButton,
    Typography,
    Tabs,
    Tab,
    Container,
    List,
    ListItem,
    ListItemAvatar,
    Avatar,
    ListItemText,
    Divider,
    Grid,
    useTheme,
    useMediaQuery,
    Badge,
} from "@mui/material";

import { BottomTab } from "../Components/Tab";
import { TopBar } from "../Components/Appbar";
import {formatColoredNumber} from "../Helper";




const sampleData = [
    {
        id: 1,
        pair: "EUR/GBP",
        time: "15:00:00",
        low: "L:235698",
        high: "H:25.3659",
        value1: "1478.256369",
        value2: "1478.246369",
        delta: "+30",
        trend: "+23.2",
        avatarSrc: "/mnt/data/339dcb9c-91ec-47d8-b940-46838228d68c.png",
    },
    {
        id: 2,
        pair: "USD/JPY",
        time: "15:10:00",
        low: "L:154002",
        high: "H:154.5689",
        value1: "176.256412",
        value2: "154.266412",
        delta: "+12",
        trend: "+23.2",
        avatarSrc: "/mnt/data/339dcb9c-91ec-47d8-b940-46838228d68c.png",
    },
    {
        id: 3,
        pair: "GBP/USD",
        time: "15:20:00",
        low: "L:125698",
        high: "H:25.5623",
        value1: "112.256974",
        value2: "154.246974",
        delta: "+44",
        trend: "+23.2",
        avatarSrc: "/mnt/data/339dcb9c-91ec-47d8-b940-46838228d68c.png",
    },
    {
        id: 4,
        pair: "AUD/CAD",
        time: "15:30:00",
        low: "L:935698",
        high: "H:25.8896",
        value1: "100.889456",
        value2: "890.879456",
        delta: "+25",
        trend: "+23.2",
        avatarSrc: "/mnt/data/339dcb9c-91ec-47d8-b940-46838228d68c.png",
    },
    {
        id: 5,
        pair: "EUR/JPY",
        time: "15:40:00",
        low: "L:178698",
        high: "H:178.3659",
        value1: "178.256398",
        value2: "181.266398",
        delta: "+55",
        trend: "+23.2",
        avatarSrc: "/mnt/data/339dcb9c-91ec-47d8-b940-46838228d68c.png",
    },
    {
        id: 6,
        pair: "USD/CHF",
        time: "15:50:00",
        low: "L:098698",
        high: "H:0.5698",
        value1: "160.896321",
        value2: "903.886321",
        delta: "+10",
        trend: "+23.2",
        avatarSrc: "/mnt/data/339dcb9c-91ec-47d8-b940-46838228d68c.png",
    },
    {
        id: 7,
        pair: "NZD/USD",
        time: "16:00:00",
        low: "L:045698",
        high: "H:0.6265",
        value1: "450.626589",
        value2: "712.616589",
        delta: "+8",
        trend: "+23.2",
        avatarSrc: "/mnt/data/339dcb9c-91ec-47d8-b940-46838228d68c.png",
    },
    {
        id: 8,
        pair: "USD/CAD",
        time: "16:10:00",
        low: "L:120698",
        high: "H:1.3566",
        value1: "932.356487",
        value2: "123.346487",
        delta: "+38",
        trend: "+23.2",
        avatarSrc: "/mnt/data/339dcb9c-91ec-47d8-b940-46838228d68c.png",
    },
    {
        id: 9,
        pair: "EUR/USD",
        time: "16:20:00",
        low: "L:102345",
        high: "H:1.0859",
        value1: "670.085612",
        value2: "166.075612",
        delta: "+15",
        trend: "+23.2",
        avatarSrc: "/mnt/data/339dcb9c-91ec-47d8-b940-46838228d68c.png",
    },
    {
        id: 10,
        pair: "GBP/JPY",
        time: "16:30:00",
        low: "L:185259",
        high: "H:185.9654",
        value1: "315.965458",
        value2: "385.955458",
        delta: "+22",
        trend: "+23.2",
        avatarSrc: "/mnt/data/339dcb9c-91ec-47d8-b940-46838228d68c.png",
    },
];


export default function ForexListPage() {
    return (
        <Box sx={{ minHeight: "100vh", bgcolor: "#0b0b0b", color: "#fff", pb: 4 }}>
            <Container sx={{ mt: 2 }}>
                <TopBar />
                <Box
                    sx={{
                        bgcolor: "#0b0b0b",
                        borderRadius: 1,
                        overflow: "hidden",
                    }}
                >
                    <List disablePadding>
                        {sampleData?.map((row, idx) => (
                            <Box key={row.id}>
                                <ListItem
                                    sx={{
                                        px: { xs: 1.5, sm: 2 },
                                        py: { xs: 1.4, sm: 1.8 },
                                        display: "flex",
                                        alignItems: "start",
                                    }}

                                >

                                    {/* LEFT SIDE : FLAG + TEXT */}
                                    <Box sx={{ display: "flex", alignItems: "center", flex: 1 }}>
                                        <Box sx={{ position: "relative", width: 50, height: 40, mr: 1.3 }}>
                                            <Avatar
                                                src={row.flag1}
                                                sx={{
                                                    width: 34,
                                                    height: 34,
                                                    position: "absolute",
                                                    left: 0,
                                                    top: 3,
                                                    border: "2px solid rgba(0,0,0,0.5)",
                                                    zIndex: 1,
                                                }}
                                            />

                                            <Avatar
                                                src={row.flag2}
                                                sx={{
                                                    width: 34,
                                                    height: 34,
                                                    position: "absolute",
                                                    left: 16,
                                                    top: 16,
                                                    border: "2px solid rgba(0,0,0,0.5)",
                                                    zIndex: 2,
                                                }}
                                            />
                                        </Box>

                                        <Box>
                                            <Typography
                                                variant="caption"
                                                sx={{
                                                    display: "block",
                                                    color: "rgba(255,255,255,0.5)",
                                                    mb: 0.3,
                                                }}
                                            >
                                                {row.time}
                                            </Typography>

                                            <Typography
                                                sx={{
                                                    fontWeight: 500,
                                                    fontSize: 16,
                                                    color: "#fff",
                                                    lineHeight: 1,
                                                }}
                                            >
                                                {row.pair}
                                            </Typography>

                                            <Box sx={{ display: "flex", alignItems: "center", mt: 0.4 }}>
                                                <Typography
                                                    sx={{
                                                        color: "#6eee3bff",
                                                        fontWeight: 500,
                                                        fontSize: 12,
                                                        mr: 0.5,
                                                    }}
                                                >
                                                    {row.delta}
                                                </Typography>

                                                <Typography
                                                    sx={{
                                                        color: "rgba(255,255,255,0.4)",
                                                        fontWeight: 600,
                                                        fontSize: 12,
                                                    }}
                                                >
                                                    ({row.trend}%)
                                                </Typography>
                                            </Box>
                                        </Box>
                                    </Box>

                                    {/* MIDDLE COLUMN */}
                                    <Box
                                        sx={{
                                            textAlign: "left",
                                            width: 100,
                                            mr: 2,
                                        }}
                                    >
                                        <Typography variant="body1">
                                            {formatColoredNumber(row.value1)}
                                        </Typography>
                                        <Typography
                                            sx={{ fontSize: 12, color: "rgba(255,255,255,0.5)" }}
                                        >
                                            {row.low}
                                        </Typography>
                                    </Box>

                                    {/* RIGHT COLUMN */}
                                    <Box
                                        sx={{
                                            textAlign: "left",
                                            width: 100,
                                        }}
                                    >
                                        <Typography variant="body1">
                                            {formatColoredNumber(row.value2)}
                                        </Typography>
                                        <Typography
                                            sx={{ fontSize: 12, color: "rgba(255,255,255,0.5)" }}
                                        >
                                            {row.high}
                                        </Typography>
                                    </Box>

                                </ListItem>


                                {idx !== sampleData.length - 1 && (
                                    <Divider
                                        sx={{ borderColor: "rgba(255, 255, 255, 0.15)" }}
                                    />
                                )}
                            </Box>
                        ))}
                    </List>
                </Box>

                <BottomTab />
            </Container>
        </Box>
    );
}
