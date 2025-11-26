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
import HomeIcon from "@mui/icons-material/Home";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import HistoryIcon from "@mui/icons-material/History";
import PersonIcon from "@mui/icons-material/Person";


export const BottomTab = () => {
    return (
        <AppBar
            position="fixed"
            sx={{
                top: "auto",
                bottom: 0,
                bgcolor: "#0b0b0b",
                borderTop: "1px solid rgba(255,255,255,0.15)",

            }}
        >
            <Toolbar sx={{ display: "flex", justifyContent: "space-around" }}>
                <Box sx={{ textAlign: "center", color: "#6eee3bff" }}>
                    <HomeIcon />
                    <Typography variant="caption">Home</Typography>
                </Box>

                <Box sx={{ textAlign: "center", color: "rgba(255,255,255,0.6)" }}>
                    <ShowChartIcon />
                    <Typography variant="caption">Trade</Typography>
                </Box>

                <Box sx={{ textAlign: "center", color: "rgba(255,255,255,0.6)" }}>
                    <HistoryIcon />
                    <Typography variant="caption">History</Typography>
                </Box>

                <Box sx={{ textAlign: "center", color: "rgba(255,255,255,0.6)" }}>
                    <PersonIcon />
                    <Typography variant="caption">Profile</Typography>
                </Box>
            </Toolbar>
        </AppBar>
    )

}
