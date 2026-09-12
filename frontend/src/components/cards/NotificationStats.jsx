export default function NotificationStats({data}){


return (

<div className="grid md:grid-cols-5 gap-4">


<div className="ui-stat">
<div className="ui-stat-label">Total</div>
<p className="ui-stat-value !text-2xl">
{data.total}
</p>
</div>


<div className="ui-stat">
<div className="ui-stat-label">Sent</div>
<p className="ui-stat-value !text-2xl" style={{ background: "none", WebkitTextFillColor: "#34d399", color: "#34d399" }}>
{data.sent}
</p>
</div>


<div className="ui-stat">
<div className="ui-stat-label">Failed</div>
<p className="ui-stat-value !text-2xl" style={{ background: "none", WebkitTextFillColor: "#fca5a5", color: "#fca5a5" }}>
{data.failed}
</p>
</div>


<div className="ui-stat">
<div className="ui-stat-label">Telegram</div>
<p className="ui-stat-value !text-2xl">
{data.telegram}
</p>
</div>


<div className="ui-stat">
<div className="ui-stat-label">Email</div>
<p className="ui-stat-value !text-2xl">
{data.email}
</p>
</div>


</div>

);

}
