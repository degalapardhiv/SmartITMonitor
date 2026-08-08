export default function NotificationStats({data}){


return (

<div className="grid md:grid-cols-5 gap-6">


<div className="bg-slate-800 p-6 rounded-xl">
<h3>Total</h3>
<p className="text-3xl font-bold">
{data.total}
</p>
</div>


<div className="bg-slate-800 p-6 rounded-xl">
<h3>Sent</h3>
<p className="text-3xl font-bold text-green-400">
{data.sent}
</p>
</div>


<div className="bg-slate-800 p-6 rounded-xl">
<h3>Failed</h3>
<p className="text-3xl font-bold text-red-400">
{data.failed}
</p>
</div>


<div className="bg-slate-800 p-6 rounded-xl">
<h3>Telegram</h3>
<p className="text-3xl font-bold">
{data.telegram}
</p>
</div>


<div className="bg-slate-800 p-6 rounded-xl">
<h3>Email</h3>
<p className="text-3xl font-bold">
{data.email}
</p>
</div>


</div>

);

}
