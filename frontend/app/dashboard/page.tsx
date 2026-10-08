import DealAnalyzer from "../../components/DealAnalyzer";
import Diagnostics from "../../components/Diagnostics";
import Tools from "../../components/Tools";
import Insights from "../../components/Insights";
import DealsTable from "../../components/DealsTable";
import QueryBox from "../../components/QueryBox";
import Predictor from "../../components/Predictor";
import LatencyDashboard from "../../components/LatencyDashboard";
export default function Page() { return (<><DealAnalyzer /><Insights /><Tools /><DealsTable /><QueryBox /><Predictor /><Diagnostics /><LatencyDashboard /></>); }
